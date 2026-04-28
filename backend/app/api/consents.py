"""API endpoints for event consents."""

import logging
from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import CurrentUser, get_current_user
from app.config import get_settings
from app.dals import ConsentDAL, EventDAL, ProfileDAL
from app.db import get_supabase_client
from app.schemas import ConsentResponse, ConsentUpdate, EventProcessingStatus
from app.services.rekognition import RekognitionError, RekognitionService
from app.utils.rekognition_helpers import build_event_collection_id

router = APIRouter(tags=["events"])
logger = logging.getLogger(__name__)


def get_consent_dal(current_user: Annotated[CurrentUser, Depends(get_current_user)]) -> ConsentDAL:
    """Dependency to get ConsentDAL with authenticated client."""
    client = get_supabase_client(current_user.access_token)
    return ConsentDAL(client)


def get_event_dal(current_user: Annotated[CurrentUser, Depends(get_current_user)]) -> EventDAL:
    """Dependency to get EventDAL with authenticated client."""
    client = get_supabase_client(current_user.access_token)
    return EventDAL(client)


def get_profile_dal(current_user: Annotated[CurrentUser, Depends(get_current_user)]) -> ProfileDAL:
    """Dependency to get ProfileDAL with authenticated client."""
    client = get_supabase_client(current_user.access_token)
    return ProfileDAL(client)


@router.get("/{event_id}/consents/me", response_model=ConsentResponse)
async def get_my_consent(
    event_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    dal: Annotated[ConsentDAL, Depends(get_consent_dal)],
) -> ConsentResponse:
    """Get the current user's consent settings for a specific event."""
    consent = await dal.get(event_id, current_user.id)
    if not consent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Consent not found. Are you a member of this event?",
        )
    return consent


@router.patch("/{event_id}/consents/me", response_model=ConsentResponse)
async def update_my_consent(
    event_id: UUID,
    data: ConsentUpdate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    consent_dal: Annotated[ConsentDAL, Depends(get_consent_dal)],
    event_dal: Annotated[EventDAL, Depends(get_event_dal)],
    profile_dal: Annotated[ProfileDAL, Depends(get_profile_dal)],
) -> ConsentResponse:
    """Update consent settings for the current user in an event."""
    event = await event_dal.get_by_id(event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found.",
        )

    now = datetime.now(timezone.utc)
    if event.ends_at and event.ends_at <= now:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Consent can no longer be updated after the event has ended.",
        )

    current_consent = await consent_dal.get(event_id, current_user.id)
    if not current_consent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Consent not found. Are you a member of this event?",
        )

    recognition_changed = data.allow_recognition is not None and (
        data.allow_recognition != current_consent.allow_recognition
    )

    if recognition_changed:
        if event.indexing_status == EventProcessingStatus.IN_PROGRESS:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Event indexing is in progress. "
                    "Please try updating recognition consent again shortly."
                ),
            )

        if event.indexing_status == EventProcessingStatus.COMPLETED:
            collection_id = build_event_collection_id(event_id)
            rekognition_service = RekognitionService()

            if data.allow_recognition is True:
                profile = await profile_dal.get_by_user_id(current_user.id)
                if not profile or not profile.photo_path:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="A profile photo is required before enabling recognition.",
                    )

                settings = get_settings()
                if not settings.s3_bucket_name:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Recognition storage is not configured.",
                    )

                try:
                    rekognition_service.index_face_from_s3(
                        collection_id=collection_id,
                        bucket_name=settings.s3_bucket_name,
                        object_key=profile.photo_path,
                        image_id=str(current_user.id),
                    )
                except (RekognitionError, RuntimeError) as exc:
                    logger.error(
                        "Failed to index face for user=%s event=%s while enabling recognition: %s",
                        current_user.id,
                        event_id,
                        exc,
                    )
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail="Failed to add your face to event recognition. Please try again.",
                    ) from exc

            if data.allow_recognition is False:
                try:
                    rekognition_service.delete_faces_by_user(
                        collection_id=collection_id,
                        user_id=current_user.id,
                    )
                except (RekognitionError, RuntimeError) as exc:
                    logger.error(
                        (
                            "Failed to delete face(s) for user=%s "
                            "event=%s while disabling recognition: %s"
                        ),
                        current_user.id,
                        event_id,
                        exc,
                    )
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail=(
                            "Failed to remove your face from event recognition. "
                            "Please try again."
                        ),
                    ) from exc

    consent = await consent_dal.update(event_id, current_user.id, data)
    if not consent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Consent not found. Are you a member of this event?",
        )
    return consent
