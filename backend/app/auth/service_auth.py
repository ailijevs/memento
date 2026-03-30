"""
Service-to-service authentication helpers for internal endpoints.

This verifies `Authorization: Bearer <token>` against a shared secret stored
in environment variables.
"""

from __future__ import annotations

from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.dependencies import verify_jwt
from app.config import get_settings

security = HTTPBearer(auto_error=False)


def require_recognition_service_auth(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> Any:
    """
    Authorize requests to recognition endpoints.

    Allows either:
    - a configured service token (preferred), or
    - a valid Supabase JWT (fallback for dev/testing).
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    settings = get_settings()

    expected_service_token = settings.recognition_service_token

    # Preferred: shared service token
    if expected_service_token and token == expected_service_token:
        return {"auth_type": "service"}

    # Fallback: accept Supabase JWT (keeps local/manual testing working).
    # This will raise 401 on invalid tokens.
    verify_jwt(token)
    return {"auth_type": "jwt"}
