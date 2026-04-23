"""Image management routes — list, detail, tags, and delete."""

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, status

from auth import CurrentUser, get_current_user
from config import settings
from services.blob_service import (
    delete_blob,
    download_blob,
    generate_read_sas_url,
)
from services.metadata_service import (
    delete_metadata,
    get_metadata,
    list_agency_metadata,
    refresh_status,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["images"])


@router.get("/images")
async def list_images(user: CurrentUser = Depends(get_current_user)):
    """List all images uploaded by the current user's agency.

    Returns metadata with current processing status (pending/completed/failed).
    Status is refreshed by checking the gold container for output files.
    """
    images = list_agency_metadata(user.agency)
    return {"agency": user.agency, "images": images, "count": len(images)}


@router.get("/images/{upload_id}")
async def get_image_detail(
    upload_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Get detailed information about a specific image upload, including a
    preview URL and AI-generated tags if processing is complete."""
    metadata = get_metadata(user.agency, upload_id)
    if metadata is None:
        raise HTTPException(status_code=404, detail="Image not found.")

    # Refresh status from gold container
    metadata = refresh_status(metadata)

    # Generate SAS URL for image preview
    preview_url = generate_read_sas_url(
        settings.bronze_container, metadata["blob_name"]
    )

    result = {**metadata, "preview_url": preview_url}

    # If completed, include AI tags
    if metadata["status"] == "completed":
        tags_data = download_blob(
            settings.gold_container, metadata["output_blob_name"]
        )
        if tags_data:
            try:
                result["tags"] = json.loads(tags_data)
            except json.JSONDecodeError:
                result["tags"] = {"raw": tags_data.decode("utf-8", errors="replace")}

    return result


@router.get("/images/{upload_id}/tags")
async def get_image_tags(
    upload_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Get the AI-generated tags (JSON output) for a processed image."""
    metadata = get_metadata(user.agency, upload_id)
    if metadata is None:
        raise HTTPException(status_code=404, detail="Image not found.")

    metadata = refresh_status(metadata)

    if metadata["status"] != "completed":
        return {
            "upload_id": upload_id,
            "status": metadata["status"],
            "tags": None,
            "message": "Image processing is not yet complete.",
        }

    tags_data = download_blob(settings.gold_container, metadata["output_blob_name"])
    if tags_data is None:
        raise HTTPException(status_code=404, detail="Tags output not found.")

    try:
        tags = json.loads(tags_data)
    except json.JSONDecodeError:
        tags = {"raw": tags_data.decode("utf-8", errors="replace")}

    return {"upload_id": upload_id, "status": "completed", "tags": tags}


@router.delete("/images/{upload_id}", status_code=status.HTTP_200_OK)
async def delete_image(
    upload_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Delete an image and all associated data (bronze blob, gold output, metadata).

    Only images belonging to the user's agency can be deleted.
    """
    metadata = get_metadata(user.agency, upload_id)
    if metadata is None:
        raise HTTPException(status_code=404, detail="Image not found.")

    # Delete from bronze container
    delete_blob(settings.bronze_container, metadata["blob_name"])

    # Delete from gold container (if output exists)
    delete_blob(settings.gold_container, metadata["output_blob_name"])

    # Delete metadata
    delete_metadata(user.agency, upload_id)

    logger.info(
        "Image deleted: %s by %s (agency: %s)",
        metadata["blob_name"],
        user.email,
        user.agency,
    )

    return {"message": "Image and associated data deleted.", "upload_id": upload_id}
