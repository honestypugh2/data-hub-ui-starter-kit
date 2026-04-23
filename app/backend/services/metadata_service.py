"""Metadata service for tracking image uploads and their processing status.

Stores per-upload metadata as JSON blobs in the ui-metadata container,
organized by agency: {agency}/{upload_id}.json
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional

from config import settings
from services.blob_service import (
    blob_exists,
    delete_blob,
    download_blob,
    ensure_container_exists,
    list_blobs,
    upload_blob,
)

logger = logging.getLogger(__name__)

METADATA_CONTAINER = settings.metadata_container


def _metadata_blob_path(agency: str, upload_id: str) -> str:
    return f"{agency}/{upload_id}.json"


def _output_blob_name(upload_id: str, original_filename: str) -> str:
    """Derive the gold-container output filename that the pipeline produces.

    The pipeline's writeToBlob does:
        sourcefile = os.path.splitext(os.path.basename(blob_name))[0]
        output = f"{sourcefile}-output.json"

    Since we upload to bronze as "{upload_id}_{sanitized_name}", the output is
    "{upload_id}_{sanitized_name_no_ext}-output.json".
    """
    base = os.path.splitext(original_filename)[0]
    bronze_stem = f"{upload_id}_{base}"
    return f"{bronze_stem}-output.json"


def create_metadata(
    upload_id: str,
    original_filename: str,
    blob_name: str,
    agency: str,
    uploaded_by: str,
    content_type: str,
    size_bytes: int,
) -> dict:
    """Create and persist a new upload metadata record."""
    ensure_container_exists(METADATA_CONTAINER)

    metadata = {
        "id": upload_id,
        "original_filename": original_filename,
        "blob_name": blob_name,
        "agency": agency,
        "uploaded_by": uploaded_by,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
        "status": "pending",
        "content_type": content_type,
        "size_bytes": size_bytes,
        "output_blob_name": _output_blob_name(upload_id, original_filename),
    }

    path = _metadata_blob_path(agency, upload_id)
    upload_blob(METADATA_CONTAINER, path, json.dumps(metadata).encode("utf-8"), "application/json")
    return metadata


def get_metadata(agency: str, upload_id: str) -> Optional[dict]:
    """Retrieve a single metadata record."""
    path = _metadata_blob_path(agency, upload_id)
    data = download_blob(METADATA_CONTAINER, path)
    if data is None:
        return None
    return json.loads(data)


def update_status(agency: str, upload_id: str, new_status: str) -> Optional[dict]:
    """Update the status field of a metadata record."""
    metadata = get_metadata(agency, upload_id)
    if metadata is None:
        return None
    metadata["status"] = new_status
    path = _metadata_blob_path(agency, upload_id)
    upload_blob(METADATA_CONTAINER, path, json.dumps(metadata).encode("utf-8"), "application/json")
    return metadata


def refresh_status(metadata: dict) -> dict:
    """Check the gold container for output and update status if needed."""
    if metadata["status"] != "pending":
        return metadata

    output_name = metadata["output_blob_name"]
    if blob_exists(settings.gold_container, output_name):
        metadata["status"] = "completed"
        path = _metadata_blob_path(metadata["agency"], metadata["id"])
        upload_blob(
            METADATA_CONTAINER,
            path,
            json.dumps(metadata).encode("utf-8"),
            "application/json",
        )

    return metadata


def list_agency_metadata(agency: str) -> list[dict]:
    """List all upload metadata for a given agency, with refreshed statuses."""
    ensure_container_exists(METADATA_CONTAINER)
    prefix = f"{agency}/"
    blob_names = list_blobs(METADATA_CONTAINER, prefix=prefix)

    results = []
    for name in blob_names:
        data = download_blob(METADATA_CONTAINER, name)
        if data:
            metadata = json.loads(data)
            metadata = refresh_status(metadata)
            results.append(metadata)

    # Sort by upload date descending
    results.sort(key=lambda m: m.get("uploaded_at", ""), reverse=True)
    return results


def delete_metadata(agency: str, upload_id: str) -> bool:
    """Delete a metadata record."""
    path = _metadata_blob_path(agency, upload_id)
    return delete_blob(METADATA_CONTAINER, path)
