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
            logger.warning("No matching signing key for token.")
            return None, _error_response(401, "Unable to find appropriate signing key.")

        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=["RS256"],
            options={"verify_aud": False, "verify_iss": False},
        )

        # Manual audience check (python-jose doesn't support list)
        token_aud = payload.get("aud", "")
        valid_audiences = {CLIENT_ID, f"api://{CLIENT_ID}"}
        if token_aud not in valid_audiences:
            logger.warning("Audience mismatch.")
            return None, _error_response(401, "Invalid or expired token.")

        # Manual issuer check (accept both v1 and v2 formats)
        token_iss = payload.get("iss", "")
        valid_issuers = {
            f"{AUTHORITY}/v2.0",
            f"https://sts.windows.net/{TENANT_ID}/",
            f"https://login.microsoftonline.com/{TENANT_ID}/v2.0",
        }
        if token_iss not in valid_issuers:
            logger.warning("Issuer mismatch.")
            return None, _error_response(401, "Invalid or expired token.")

        return CurrentUser(payload), None

    except JWTError as e:
        logger.warning("JWT validation failed: %s", e)
        return None, _error_response(401, "Invalid or expired token.")

        # --- DIAGNOSTIC LOGGING (uncomment for debugging auth issues) ---
        # Decodes the token WITHOUT verification to inspect claims.
        # DO NOT enable in production — exposes token claims in logs.
        #
        # unverified = jwt.get_unverified_claims(token)
        # token_aud = unverified.get("aud")
        # token_iss = unverified.get("iss")
        # expected_aud = [CLIENT_ID, f"api://{CLIENT_ID}"]
        # expected_iss = f"{AUTHORITY}/v2.0"
        # logger.info(
        #     "JWT debug — token aud=%s, iss=%s | expected aud=%s, iss=%s",
        #     token_aud, token_iss, expected_aud, expected_iss,
        # )
        # --- END DIAGNOSTIC LOGGING ---

    except httpx.HTTPError as e:
        logger.error("Failed to fetch OIDC keys: %s", e)
        return None, _error_response(503, "Authentication service unavailable.")
