"""
Service-to-service authentication for internal endpoints.

Uses two separate credentials:
- ``Authorization: Bearer <user JWT>`` — authenticates the end user
  (reuses the existing ``get_current_user`` dependency).
- ``X-Recognition-Api-Key: <api key>`` — authenticates the calling
  client/service (e.g. Mentra app or web frontend).

The raw API key is hashed with SHA-256 and checked against configured
hashes in ``settings.hash_to_client``.
"""

from __future__ import annotations

import hashlib
import logging

from fastapi import Header, HTTPException, status

from app.config import get_settings

logger = logging.getLogger(__name__)


def _hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def verify_recognition_api_key(
    x_recognition_api_key: str | None = Header(None),
) -> str:
    """
    Verify the ``X-Recognition-Api-Key`` header by hash lookup.

    When no key-hash mappings are configured, the check is
    skipped so local development keeps working without extra setup.
    """
    settings = get_settings()
    hash_to_client = settings.hash_to_client

    if not hash_to_client:
        logger.info("Recognition API key check bypassed: no key hashes configured.")
        return "unknown"

    if x_recognition_api_key is None:
        logger.warning("Recognition API key auth failed: missing X-Recognition-Api-Key header.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Recognition-Api-Key header",
        )

    candidate_hash = _hash_api_key(x_recognition_api_key)
    client_name = hash_to_client.get(candidate_hash)
    if not client_name:
        logger.warning(
            "Recognition API key auth failed: key hash did not match any configured client."
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid recognition API key",
        )

    logger.info("Recognition API key auth passed for client=%s", client_name)
    return client_name
