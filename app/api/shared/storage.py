"""Azure Blob Storage operations — upload, download, list, delete, and metadata tracking."""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional

from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient

logger = logging.getLogger(__name__)

STORAGE_ACCOUNT_URL = os.environ.get("AZURE_STORAGE_ACCOUNT_URL", "")
STORAGE_CONNECTION_STRING = os.environ.get("AZURE_STORAGE_CONNECTION_STRING", "")
BRONZE_CONTAINER = os.environ.get("BRONZE_CONTAINER", "bronze")
GOLD_CONTAINER = os.environ.get("GOLD_CONTAINER", "gold")
METADATA_CONTAINER = os.environ.get("METADATA_CONTAINER", "ui-metadata")
MAX_UPLOAD_SIZE_MB = int(os.environ.get("MAX_UPLOAD_SIZE_MB", "20"))
ALLOWED_EXTENSIONS = os.environ.get("ALLOWED_EXTENSIONS", "jpg,jpeg,png")


def _get_blob_service_client() -> BlobServiceClient:
    """Create a BlobServiceClient using connection string or managed identity."""
    if STORAGE_CONNECTION_STRING:
        return BlobServiceClient.from_connection_string(STORAGE_CONNECTION_STRING)
    credential = DefaultAzureCredential()
    return BlobServiceClient(account_url=STORAGE_ACCOUNT_URL, credential=credential)


_client: Optional[BlobServiceClient] = None


def get_blob_client() -> BlobServiceClient:
    global _client
    if _client is None:
        _client = _get_blob_service_client()
    return _client


def ensure_container_exists(container_name: str) -> None:
    """Create the container if it does not already exist."""
    client = get_blob_client()
    container = client.get_container_client(container_name)
    if not container.exists():
        container.create_container()


def upload_blob(container_name: str, blob_name: str, data: bytes, content_type: str) -> str:
    """Upload bytes to a blob and return the blob URL."""
    client = get_blob_client()
    blob = client.get_blob_client(container=container_name, blob=blob_name)
    blob.upload_blob(
        data,
        overwrite=True,
        content_settings={"content_type": content_type},
    )
    return blob.url


def download_blob(container_name: str, blob_name: str) -> Optional[bytes]:
    """Download blob content. Returns None if blob does not exist."""
    client = get_blob_client()
    blob = client.get_blob_client(container=container_name, blob=blob_name)
    try:
        return blob.download_blob().readall()
    except Exception:
        return None


def blob_exists(container_name: str, blob_name: str) -> bool:
    """Check whether a blob exists in the given container."""
    client = get_blob_client()
    blob = client.get_blob_client(container=container_name, blob=blob_name)
    return blob.exists()


def delete_blob(container_name: str, blob_name: str) -> bool:
    """Delete a blob. Returns True if deleted, False if not found."""
    client = get_blob_client()
    blob = client.get_blob_client(container=container_name, blob=blob_name)
    try:
        blob.delete_blob()
        return True
    except Exception:
        return False


def list_blobs(container_name: str, prefix: Optional[str] = None) -> list[str]:
    """List blob names in a container, optionally filtered by prefix."""
    client = get_blob_client()
    container = client.get_container_client(container_name)
    return [b.name for b in container.list_blobs(name_starts_with=prefix)]


# ---------------------------------------------------------------------------
# Metadata helpers (stored as JSON blobs in the metadata container)
# ---------------------------------------------------------------------------

def _metadata_blob_path(agency: str, upload_id: str) -> str:
    return f"{agency}/{upload_id}.json"


def _output_blob_name(upload_id: str, original_filename: str) -> str:
    """Derive the gold-container output filename that the pipeline produces."""
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


def refresh_status(metadata: dict) -> dict:
    """Check the gold container for output and update status if needed."""
    if metadata["status"] != "pending":
        return metadata

    output_name = metadata["output_blob_name"]
    if blob_exists(GOLD_CONTAINER, output_name):
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

    results.sort(key=lambda m: m.get("uploaded_at", ""), reverse=True)
    return results


def delete_metadata(agency: str, upload_id: str) -> bool:
    """Delete a metadata record."""
    path = _metadata_blob_path(agency, upload_id)
    return delete_blob(METADATA_CONTAINER, path)
