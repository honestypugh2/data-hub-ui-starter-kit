"""Azure Entra ID JWT token validation for Azure Functions."""

import logging
import os
from dataclasses import dataclass, field
from typing import Optional

import azure.functions as func
import httpx
from jose import JWTError, jwt  # type: ignore[import-untyped]

logger = logging.getLogger(__name__)

# Cache for OIDC signing keys
_jwks_cache: Optional[dict] = None

TENANT_ID = os.environ.get("AZURE_TENANT_ID", "")
CLIENT_ID = os.environ.get("AZURE_CLIENT_ID", "")
AUTHORITY = os.environ.get(
    "AZURE_AUTHORITY", f"https://login.microsoftonline.com/{TENANT_ID}"
)


@dataclass
class CurrentUser:
    """Represents the authenticated user extracted from the JWT token."""

    claims: dict = field(repr=False)
    email: str = ""
    name: str = ""
    oid: str = ""
    agency: str = "default"

    def __init__(self, claims: dict):
        self.claims = claims
        self.email = claims.get("preferred_username", claims.get("email", ""))
        self.name = claims.get("name", "")
        self.oid = claims.get("oid", "")
        self.agency = claims.get("department", claims.get("agency", "default"))


async def _get_signing_keys() -> dict:
    """Fetch and cache OIDC signing keys from Entra ID."""
    global _jwks_cache
    if _jwks_cache is not None:
        return _jwks_cache

    oidc_url = f"{AUTHORITY}/v2.0/.well-known/openid-configuration"
    async with httpx.AsyncClient() as client:
        oidc_resp = await client.get(oidc_url)
        oidc_resp.raise_for_status()
        jwks_uri = oidc_resp.json()["jwks_uri"]

        jwks_resp = await client.get(jwks_uri)
        jwks_resp.raise_for_status()
        _jwks_cache = jwks_resp.json()

    assert _jwks_cache is not None
    return _jwks_cache


def _find_rsa_key(token: str, jwks: dict) -> Optional[dict]:
    """Match the token's kid to an RSA key in the JWKS."""
    unverified_header = jwt.get_unverified_header(token)
    kid = unverified_header.get("kid")
    for key in jwks.get("keys", []):
        if key["kid"] == kid:
            return key
    return None


def _error_response(status_code: int, detail: str) -> func.HttpResponse:
    """Return a JSON error response."""
    import json

    return func.HttpResponse(
        json.dumps({"detail": detail}),
        status_code=status_code,
        mimetype="application/json",
    )


async def validate_token(req: func.HttpRequest) -> tuple[Optional[CurrentUser], Optional[func.HttpResponse]]:
    """Validate the Entra ID JWT from the Authorization header.

    Returns (CurrentUser, None) on success, or (None, HttpResponse) on failure.
    """
    auth_header = req.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None, _error_response(401, "Missing or invalid Authorization header.")

    token = auth_header[7:]

    try:
        jwks = await _get_signing_keys()
        rsa_key = _find_rsa_key(token, jwks)

        if rsa_key is None:
            return None, _error_response(401, "Unable to find appropriate signing key.")

        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=["RS256"],
            audience=CLIENT_ID,
            issuer=f"{AUTHORITY}/v2.0",
        )

        return CurrentUser(payload), None

    except JWTError as e:
        logger.warning("JWT validation failed: %s", e)
        return None, _error_response(401, "Invalid or expired token.")

    except httpx.HTTPError as e:
        logger.error("Failed to fetch OIDC keys: %s", e)
        return None, _error_response(503, "Authentication service unavailable.")
