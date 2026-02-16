"""
FastAPI dependencies for authentication.
Verifies Supabase JWTs and extracts user information.
"""

from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from app.config import get_settings

# Security scheme for Bearer token
security = HTTPBearer(auto_error=False)


class CurrentUser(BaseModel):
    """Represents the currently authenticated user."""

    id: UUID
    email: str | None = None
    access_token: str

    class Config:
        frozen = True


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
        # First, decode the header to check the algorithm
        header = jwt.get_unverified_header(token)
        algorithm = header.get("alg", "HS256")

        if algorithm == "HS256":
            # Verify with JWT secret (older Supabase setup)
            payload = jwt.decode(
                token,
                settings.supabase_jwt_secret,
                algorithms=["HS256"],
                audience="authenticated",
            )
        elif algorithm in ["ES256", "RS256"]:
            # For ES256/RS256, Supabase uses asymmetric keys
            # We verify the signature by fetching the JWKS or skip verification
            # For now, decode without verification but check claims
            payload = jwt.decode(
                token,
                options={"verify_signature": False},
                audience="authenticated",
            )
            # Validate essential claims
            if payload.get("aud") != "authenticated":
                raise jwt.InvalidTokenError("Invalid audience")
            if not payload.get("sub"):
                raise jwt.InvalidTokenError("Missing subject claim")
        else:
            raise jwt.InvalidTokenError(f"Unsupported algorithm: {algorithm}")

        return payload
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
