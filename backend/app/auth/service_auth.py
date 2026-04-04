"""
Service-to-service authentication for internal endpoints.

Uses two separate credentials:
- ``Authorization: Bearer <user JWT>`` — authenticates the end user
  (reuses the existing ``get_current_user`` dependency).
- ``X-Service-Token: <shared secret>`` — authenticates the calling
  service (e.g. Mentra cloud app).

The service token is compared with ``secrets.compare_digest`` to
avoid timing-based side-channel leaks.
"""

from __future__ import annotations

import secrets

from fastapi import Header, HTTPException, status

from app.config import get_settings


def verify_service_token(
    x_service_token: str | None = Header(None),
) -> None:
    """
    Verify the ``X-Service-Token`` header against the configured secret.

    When ``RECOGNITION_SERVICE_TOKEN`` is **not** configured the check is
    skipped so local development keeps working without extra setup.
    """
    settings = get_settings()
    expected = settings.recognition_service_token

    if not expected:
        return

    if x_service_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Service-Token header",
        )

    if not secrets.compare_digest(x_service_token, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid service token",
        )
