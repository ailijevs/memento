"""
FastAPI dependencies for authentication.
Verifies Supabase JWTs and extracts user information.
"""

from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict

from app.config import get_settings

# Security scheme for Bearer token
security = HTTPBearer(auto_error=False)


class CurrentUser(BaseModel):
    """Represents the currently authenticated user."""

    model_config = ConfigDict(frozen=True)

    id: UUID
    email: str | None = None
    access_token: str


@lru_cache
def get_jwk_client() -> jwt.PyJWKClient:
    """Create and cache JWK client for Supabase asymmetric JWTs."""
    settings = get_settings()
    jwks_url = f"{settings.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"
    return jwt.PyJWKClient(jwks_url)


def verify_jwt(token: str) -> dict:
    """
    Verify and decode a Supabase JWT.

    Args:
        token: The JWT access token from the Authorization header.

    Returns:
        The decoded JWT payload.

    Raises:
        HTTPException: If the token is invalid or expired.
    """
    settings = get_settings()

    try:
        header = jwt.get_unverified_header(token)
        alg = header.get("alg")

        # Legacy/project-secret flow
        if alg == "HS256":
            payload = jwt.decode(
                token,
                settings.supabase_jwt_secret,
                algorithms=["HS256"],
                audience="authenticated",
            )
            return payload

        # Modern Supabase flow (asymmetric JWTs, e.g. ES256/RS256)
        if alg in {"ES256", "RS256"}:
            signing_key = get_jwk_client().get_signing_key_from_jwt(token)
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=[alg],
                audience="authenticated",
                issuer=f"{settings.supabase_url.rstrip('/')}/auth/v1",
            )
            return payload

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: unsupported algorithm {alg}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> CurrentUser:
    """
    Dependency to get the current authenticated user.
    Raises 401 if not authenticated.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = verify_jwt(credentials.credentials)

    # Extract user ID from 'sub' claim
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing user ID",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return CurrentUser(
        id=UUID(user_id),
        email=payload.get("email"),
        access_token=credentials.credentials,
    )


async def get_current_user_optional(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> CurrentUser | None:
    """
    Dependency to optionally get the current user.
    Returns None if not authenticated (doesn't raise).
    """
    if credentials is None:
        return None

    try:
        payload = verify_jwt(credentials.credentials)
        user_id = payload.get("sub")
        if not user_id:
            return None

        return CurrentUser(
            id=UUID(user_id),
            email=payload.get("email"),
            access_token=credentials.credentials,
        )
    except HTTPException:
        return None
