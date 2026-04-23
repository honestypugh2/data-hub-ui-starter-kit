"""get_results — HTTP-triggered Azure Function for retrieving AI-generated tags.

GET /api/images/{id}/tags  — return AI tags for a processed image
"""

import json
import logging

import azure.functions as func

from shared.auth import validate_token
from shared.storage import (
    GOLD_CONTAINER,
    download_blob,
    get_metadata,
    refresh_status,
)

logger = logging.getLogger(__name__)

bp = func.Blueprint()


def _json(body: dict, status_code: int = 200) -> func.HttpResponse:
    return func.HttpResponse(
        json.dumps(body), status_code=status_code, mimetype="application/json"
    )


@bp.route(route="images/{upload_id}/tags", methods=["GET"])
async def get_image_tags(req: func.HttpRequest) -> func.HttpResponse:
    """Get the AI-generated tags (JSON output) for a processed image."""
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

    if metadata["status"] != "completed":
        return _json(
            {
                "upload_id": upload_id,
                "status": metadata["status"],
                "tags": None,
                "message": "Image processing is not yet complete.",
            }
        )

    tags_data = download_blob(GOLD_CONTAINER, metadata["output_blob_name"])
    if tags_data is None:
        return _json({"detail": "Tags output not found."}, 404)

    try:
        tags = json.loads(tags_data)
    except json.JSONDecodeError:
        tags = {"raw": tags_data.decode("utf-8", errors="replace")}

    return _json({"upload_id": upload_id, "status": "completed", "tags": tags})
