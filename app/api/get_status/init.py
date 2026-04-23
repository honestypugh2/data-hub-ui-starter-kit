"""get_status — HTTP-triggered Azure Functions for listing images and image detail.

GET /api/images           — list all images for the caller's agency
GET /api/images/{id}      — get detail + preview URL for one image
DELETE /api/images/{id}   — delete an image and associated data
"""

import json
import logging

import azure.functions as func

from shared.auth import validate_token
from shared.sas import generate_read_sas_url
from shared.storage import (
    BRONZE_CONTAINER,
    GOLD_CONTAINER,
    delete_blob,
    delete_metadata,
    download_blob,
    get_metadata,
    list_agency_metadata,
    refresh_status,
)

logger = logging.getLogger(__name__)

bp = func.Blueprint()


def _json(body: dict, status_code: int = 200) -> func.HttpResponse:
    return func.HttpResponse(
        json.dumps(body), status_code=status_code, mimetype="application/json"
    )


@bp.route(route="images", methods=["GET"])
async def list_images(req: func.HttpRequest) -> func.HttpResponse:
    """List all images uploaded by the current user's agency."""
    user, err = await validate_token(req)
    if err:
        return err

    if user is None:
        return _json({"detail": "Unauthorized"}, 401)

    images = list_agency_metadata(user.agency)
    return _json({"agency": user.agency, "images": images, "count": len(images)})


@bp.route(route="images/{upload_id}", methods=["GET"])
async def get_image_detail(req: func.HttpRequest) -> func.HttpResponse:
    """Get detailed information about a specific image upload."""
    user, err = await validate_token(req)
    if err:
        return err

    if user is None:
        return _json({"detail": "Unauthorized"}, 401)

    upload_id = req.route_params.get("upload_id", "")
    metadata = get_metadata(user.agency, upload_id)
    if metadata is None:
        return _json({"detail": "Image not found."}, 404)

    metadata = refresh_status(metadata)

    preview_url = generate_read_sas_url(BRONZE_CONTAINER, metadata["blob_name"])
    result = {**metadata, "preview_url": preview_url}

    # If completed, include AI tags
    if metadata["status"] == "completed":
        tags_data = download_blob(GOLD_CONTAINER, metadata["output_blob_name"])
        if tags_data:
            try:
                result["tags"] = json.loads(tags_data)
            except json.JSONDecodeError:
                result["tags"] = {"raw": tags_data.decode("utf-8", errors="replace")}

    return _json(result)


@bp.route(route="images/{upload_id}", methods=["DELETE"])
async def delete_image(req: func.HttpRequest) -> func.HttpResponse:
    """Delete an image and all associated data."""
    user, err = await validate_token(req)
    if err:
        return err

    if user is None:
        return _json({"detail": "Unauthorized"}, 401)

    upload_id = req.route_params.get("upload_id", "")
    metadata = get_metadata(user.agency, upload_id)
    if metadata is None:
        return _json({"detail": "Image not found."}, 404)

    delete_blob(BRONZE_CONTAINER, metadata["blob_name"])
    delete_blob(GOLD_CONTAINER, metadata["output_blob_name"])
    delete_metadata(user.agency, upload_id)

    logger.info(
        "Image deleted: %s by %s (agency: %s)",
        metadata["blob_name"],
        user.email,
        user.agency,
    )

    return _json({"message": "Image and associated data deleted.", "upload_id": upload_id})
