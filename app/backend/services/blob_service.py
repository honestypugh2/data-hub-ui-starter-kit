"""Azure Blob Storage service for upload, download, list, and delete operations."""

import logging
from datetime import datetime, timedelta, timezone

from azure.identity import DefaultAzureCredential
from azure.storage.blob import (
    BlobSasPermissions,
    BlobServiceClient,
    UserDelegationKey,
    generate_blob_sas,
)

from config import settings

logger = logging.getLogger(__name__)


def _get_blob_service_client() -> BlobServiceClient:
    """Create a BlobServiceClient using connection string or managed identity."""
    if settings.azure_storage_connection_string:
        return BlobServiceClient.from_connection_string(
            settings.azure_storage_connection_string
        )
    credential = DefaultAzureCredential()
    return BlobServiceClient(
        account_url=settings.azure_storage_account_url, credential=credential
    )


_client: BlobServiceClient | None = None


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


def download_blob(container_name: str, blob_name: str) -> bytes | None:
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


def list_blobs(container_name: str, prefix: str | None = None) -> list[str]:
    """List blob names in a container, optionally filtered by prefix."""
    client = get_blob_client()
    container = client.get_container_client(container_name)
    return [b.name for b in container.list_blobs(name_starts_with=prefix)]


def generate_read_sas_url(container_name: str, blob_name: str, expiry_minutes: int = 30) -> str:
    """Generate a SAS URL for reading a blob (used for image preview)."""
    client = get_blob_client()
    blob = client.get_blob_client(container=container_name, blob=blob_name)

    # Use user delegation key if using managed identity, otherwise account key
    try:
        delegation_key: UserDelegationKey = client.get_user_delegation_key(
            key_start_time=datetime.now(timezone.utc),
            key_expiry_time=datetime.now(timezone.utc) + timedelta(minutes=expiry_minutes),
        )
        sas_token = generate_blob_sas(
            account_name=client.account_name,
            container_name=container_name,
            blob_name=blob_name,
            user_delegation_key=delegation_key,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.now(timezone.utc) + timedelta(minutes=expiry_minutes),
        )
    except Exception:
        # Fallback: return direct URL (works if storage allows public access or caller has token)
        return blob.url

    return f"{blob.url}?{sas_token}"
