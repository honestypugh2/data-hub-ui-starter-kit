"""SAS token generation for blob read and write access."""

import logging
from datetime import datetime, timedelta, timezone

from azure.storage.blob import (
    BlobSasPermissions,
    UserDelegationKey,
    generate_blob_sas,
)

from shared.storage import get_blob_client

logger = logging.getLogger(__name__)


def generate_read_sas_url(
    container_name: str, blob_name: str, expiry_minutes: int = 30
) -> str:
    """Generate a time-limited SAS URL for reading a blob (image preview)."""
    client = get_blob_client()
    blob = client.get_blob_client(container=container_name, blob=blob_name)

    try:
        delegation_key: UserDelegationKey = client.get_user_delegation_key(
            key_start_time=datetime.now(timezone.utc),
            key_expiry_time=datetime.now(timezone.utc)
            + timedelta(minutes=expiry_minutes),
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
        # Fallback: return direct URL (works if storage allows public access
        # or caller already has a token)
        return blob.url

    return f"{blob.url}?{sas_token}"


def generate_write_sas_url(
    container_name: str, blob_name: str, expiry_minutes: int = 15
) -> str:
    """Generate a time-limited SAS URL for writing (uploading) a blob."""
    client = get_blob_client()
    blob = client.get_blob_client(container=container_name, blob=blob_name)

    delegation_key: UserDelegationKey = client.get_user_delegation_key(
        key_start_time=datetime.now(timezone.utc),
        key_expiry_time=datetime.now(timezone.utc)
        + timedelta(minutes=expiry_minutes),
    )
    sas_token = generate_blob_sas(
        account_name=client.account_name,
        container_name=container_name,
        blob_name=blob_name,
        user_delegation_key=delegation_key,
        permission=BlobSasPermissions(write=True, create=True),
        expiry=datetime.now(timezone.utc) + timedelta(minutes=expiry_minutes),
    )

    return f"{blob.url}?{sas_token}"
