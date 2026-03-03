"""Recognition API endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, status

from app.auth.dependencies import get_current_user
from app.db.supabase import get_admin_client
from app.services.recognition_publisher import RecognitionPublisher

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/recognition", tags=["recognition"])


@router.post("/cleanup", status_code=status.HTTP_200_OK)
async def cleanup_recognition_results(
    current_user: dict = Depends(get_current_user),
    max_age_minutes: int = 5,
):
    """Delete stale recognition results older than max_age_minutes.

    Keeps the recognition_results table lightweight and privacy-friendly.
    """
    admin_client = get_admin_client()
    publisher = RecognitionPublisher(admin_client)
    deleted = publisher.cleanup_old_results(max_age_minutes=max_age_minutes)

    return {
        "deleted_count": deleted,
        "max_age_minutes": max_age_minutes,
    }
