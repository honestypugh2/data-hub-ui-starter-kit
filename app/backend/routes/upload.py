"""Image upload route — single image upload with validation."""

import logging
import os
import re
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from auth import CurrentUser, get_current_user
from config import settings
from services.blob_service import ensure_container_exists, upload_blob
from services.metadata_service import create_metadata

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["upload"])


def _sanitize_filename(filename: str) -> str:
    """Remove unsafe characters from filename, keep extension."""
    name, ext = os.path.splitext(filename)
    safe_name = re.sub(r"[^a-zA-Z0-9_\-]", "_", name)
    return f"{safe_name}{ext.lower()}"


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_image(
    file: UploadFile = File(...),
    user: CurrentUser = Depends(get_current_user),
):
    """Upload a single image (JPG/PNG) to the bronze container for AI processing.

    The image is stored as {upload_id}_{sanitized_filename} in the bronze container.
    The existing Azure Durable Functions pipeline will automatically trigger on the
    blob upload and process the image through callAoaiMultiModal.
    """
    # Validate file extension
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required.")

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in settings.allowed_extensions_set:
        raise HTTPException(
            status_code=400,
            detail=f"File type '.{ext}' not allowed. Accepted: {settings.allowed_extensions}",
        )

    # Validate content type
    allowed_content_types = {"image/jpeg", "image/png"}
    if file.content_type not in allowed_content_types:
        raise HTTPException(
            status_code=400,
            detail=f"Content type '{file.content_type}' not allowed.",
        )

    # Read and validate size
    content = await file.read()
    if len(content) > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"File exceeds maximum size of {settings.max_upload_size_mb} MB.",
        )

    if len(content) == 0:
        raise HTTPException(status_code=400, detail="File is empty.")

    # Generate unique blob name to avoid collisions
    upload_id = str(uuid.uuid4())[:8]
    safe_filename = _sanitize_filename(file.filename)
    blob_name = f"{upload_id}_{safe_filename}"

    # Upload to bronze container (triggers the existing pipeline)
    ensure_container_exists(settings.bronze_container)
    blob_url = upload_blob(
        settings.bronze_container,
        blob_name,
        content,
        file.content_type,
    )

    # Create metadata record for tracking
    metadata = create_metadata(
        upload_id=upload_id,
        original_filename=safe_filename,
        blob_name=blob_name,
        agency=user.agency,
        uploaded_by=user.email,
        content_type=file.content_type,
        size_bytes=len(content),
    )

    logger.info(
        "Image uploaded: %s by %s (agency: %s)", blob_name, user.email, user.agency
    )

    return {
        "message": "Image uploaded successfully. Processing will begin shortly.",
        "upload_id": upload_id,
        "filename": safe_filename,
        "status": "pending",
        "blob_name": blob_name,
    }
