"""upload_initiate — HTTP-triggered Azure Function for image upload.

POST /api/upload
Validates the request, generates a write SAS URL for the bronze container,
creates a metadata record, and returns the SAS URL so the UI can upload
the image directly to Blob Storage (triggering the existing Durable
Functions pipeline).
"""

import json
import logging
import os
import re
import uuid

import azure.functions as func

from shared.auth import validate_token
from shared.sas import generate_write_sas_url
from shared.storage import (
    ALLOWED_EXTENSIONS,
    BRONZE_CONTAINER,
    MAX_UPLOAD_SIZE_MB,
    create_metadata,
    ensure_container_exists,
)

logger = logging.getLogger(__name__)

bp = func.Blueprint()

ALLOWED_EXT_SET = {ext.strip().lower() for ext in ALLOWED_EXTENSIONS.split(",")}
MAX_UPLOAD_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png"}


def _json(body: dict, status_code: int = 200) -> func.HttpResponse:
    return func.HttpResponse(
        json.dumps(body), status_code=status_code, mimetype="application/json"
    )


def _sanitize_filename(filename: str) -> str:
    """Remove unsafe characters from filename, keep extension."""
    name, ext = os.path.splitext(filename)
    safe_name = re.sub(r"[^a-zA-Z0-9_\-]", "_", name)
    return f"{safe_name}{ext.lower()}"


@bp.route(route="upload", methods=["POST"])
async def upload_initiate(req: func.HttpRequest) -> func.HttpResponse:
    """Return a SAS URL for uploading an image (JPG/PNG) to the bronze container."""
    user, err = await validate_token(req)
    if err:
        return err

    if user is None:
        return _json({"detail": "Unauthorized"}, 401)

    # --- Parse JSON body ---
    try:
        body = req.get_json()
    except ValueError:
        return _json({"detail": "Invalid JSON body."}, 400)

    filename = body.get("filename", "")
    content_type = body.get("content_type", "")
    size_bytes = body.get("size_bytes", 0)

    if not filename:
        return _json({"detail": "Filename is required."}, 400)

    # Validate extension
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXT_SET:
        return _json(
            {"detail": f"File type '.{ext}' not allowed. Accepted: {ALLOWED_EXTENSIONS}"},
            400,
        )

    # Validate content type
    if content_type not in ALLOWED_CONTENT_TYPES:
        return _json({"detail": f"Content type '{content_type}' not allowed."}, 400)

    # Validate size
    if not isinstance(size_bytes, int) or size_bytes <= 0:
        return _json({"detail": "File size must be greater than zero."}, 400)

    if size_bytes > MAX_UPLOAD_BYTES:
        return _json(
            {"detail": f"File exceeds maximum size of {MAX_UPLOAD_SIZE_MB} MB."}, 400
        )

    # Generate unique blob name
    upload_id = str(uuid.uuid4())[:8]
    safe_filename = _sanitize_filename(filename)
    blob_name = f"{upload_id}_{safe_filename}"

    # Ensure container exists and generate write SAS URL
    ensure_container_exists(BRONZE_CONTAINER)
    sas_url = generate_write_sas_url(BRONZE_CONTAINER, blob_name)

    # Create metadata record for tracking
    create_metadata(
        upload_id=upload_id,
        original_filename=safe_filename,
        blob_name=blob_name,
        agency=user.agency,
        uploaded_by=user.email,
        content_type=content_type,
        size_bytes=size_bytes,
    )

    logger.info(
        "Upload authorized: %s by %s (agency: %s)", blob_name, user.email, user.agency
    )

    return _json(
        {
            "message": "Upload authorized. Use the SAS URL to upload directly.",
            "upload_id": upload_id,
            "filename": safe_filename,
            "status": "pending",
            "blob_name": blob_name,
            "sas_url": sas_url,
        },
        201,
    )
