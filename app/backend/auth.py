"""Azure Entra ID JWT token validation middleware."""

import logging
from typing import Optional

import httpx
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from config import settings

logger = logging.getLogger(__name__)

security = HTTPBearer()

# Cache for OIDC signing keys
_jwks_cache: Optional[dict] = None


async def _get_signing_keys() -> dict:
    """Fetch and cache OIDC signing keys from Entra ID."""
    global _jwks_cache
    if _jwks_cache is not None:
        return _jwks_cache

    oidc_url = f"{settings.authority_url}/v2.0/.well-known/openid-configuration"
    async with httpx.AsyncClient() as client:
        oidc_resp = await client.get(oidc_url)
        oidc_resp.raise_for_status()
        jwks_uri = oidc_resp.json()["jwks_uri"]

        jwks_resp = await client.get(jwks_uri)
        jwks_resp.raise_for_status()
        _jwks_cache = jwks_resp.json()

    return _jwks_cache


def _find_rsa_key(token: str, jwks: dict) -> Optional[dict]:
    """Match the token's kid to an RSA key in the JWKS."""
    unverified_header = jwt.get_unverified_header(token)
    kid = unverified_header.get("kid")
    for key in jwks.get("keys", []):
        if key["kid"] == kid:
            return key
    return None


class CurrentUser:
    """Represents the authenticated user extracted from the JWT token."""

    def __init__(self, claims: dict):
        self.claims = claims
        self.email = claims.get("preferred_username", claims.get("email", ""))
        self.name = claims.get("name", "")
        self.oid = claims.get("oid", "")
        # Agency can come from department claim, group, or custom claim
        self.agency = claims.get("department", claims.get("agency", "default"))


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> CurrentUser:
    """Validate the Entra ID JWT and return the current user."""
    token = credentials.credentials

    try:
        jwks = await _get_signing_keys()
        rsa_key = _find_rsa_key(token, jwks)

        if rsa_key is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unable to find appropriate signing key.",
            )

        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=["RS256"],
            audience=settings.azure_client_id,
            issuer=f"{settings.authority_url}/v2.0",
        )

        return CurrentUser(payload)

    except JWTError as e:
        logger.warning("JWT validation failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
        )
    except httpx.HTTPError as e:
        logger.error("Failed to fetch OIDC keys: %s", e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable.",
        )
