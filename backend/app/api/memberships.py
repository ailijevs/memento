"""API endpoints for event memberships."""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import CurrentUser, get_current_user
from app.dals import ConsentDAL, EventDAL, MembershipDAL
from app.db import get_supabase_client
from app.schemas import (
    ConsentCreate,
    EventProcessingStatus,
    MembershipCreate,
    MembershipResponse,
)
from app.services.rekognition import RekognitionError, RekognitionService
from app.utils.rekognition_helpers import build_event_collection_id

router = APIRouter(tags=["events"])
logger = logging.getLogger(__name__)


def get_membership_dal(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> MembershipDAL:
    """Dependency to get MembershipDAL with authenticated client."""
    client = get_supabase_client(current_user.access_token)
    return MembershipDAL(client)


def get_consent_dal(current_user: Annotated[CurrentUser, Depends(get_current_user)]) -> ConsentDAL:
    """Dependency to get ConsentDAL with authenticated client."""
    client = get_supabase_client(current_user.access_token)
    return ConsentDAL(client)


def get_event_dal(current_user: Annotated[CurrentUser, Depends(get_current_user)]) -> EventDAL:
    """Dependency to get EventDAL with authenticated client."""
    client = get_supabase_client(current_user.access_token)
    return EventDAL(client)


@router.post(
    "/{event_id}/join", response_model=MembershipResponse, status_code=status.HTTP_201_CREATED
)
async def join_event(
    event_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    membership_dal: Annotated[MembershipDAL, Depends(get_membership_dal)],
    consent_dal: Annotated[ConsentDAL, Depends(get_consent_dal)],
    event_dal: Annotated[EventDAL, Depends(get_event_dal)],
) -> MembershipResponse:
    """
    Join an event. Creates both membership and consent records.
    Consent defaults to False (explicit opt-in required).
    """
    # Check if already a member
    existing = await membership_dal.get(event_id, current_user.id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You are already a member of this event.",
        )

    event = await event_dal.get_by_id(event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found.",
        )

    event_start = event.starts_at
    if event_start is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Event start time is unexpectedly missing.",
        )

    join_cutoff = event_start - timedelta(minutes=20)
    now = datetime.now(timezone.utc)
    if now > join_cutoff:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only join an event at least 20 minutes before it starts.",
        )

    # Create membership
    membership = await membership_dal.join_event(
        current_user.id, MembershipCreate(event_id=event_id)
    )

    # Create default consent (both False)
    await consent_dal.create(
        current_user.id,
        ConsentCreate(
            event_id=event_id,
            allow_profile_display=False,
            allow_recognition=False,
        ),
    )

    return membership


@router.delete("/{event_id}/leave", status_code=status.HTTP_204_NO_CONTENT)
async def leave_event(
    event_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    membership_dal: Annotated[MembershipDAL, Depends(get_membership_dal)],
    consent_dal: Annotated[ConsentDAL, Depends(get_consent_dal)],
    event_dal: Annotated[EventDAL, Depends(get_event_dal)],
) -> None:
    """
    Leave an event with indexing-aware cleanup behavior.

    - If indexing is pending: delete consent + membership immediately.
    - If indexing is in progress: return 409 so the client can retry.
    - If indexing completes: delete user's faces from collection, then delete rows.
    - If indexing fails: apply a short grace wait/recheck, then allow row deletion.
    """
    event = await event_dal.get_by_id(event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found.",
        )

    membership = await membership_dal.get(event_id, current_user.id)
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You are not a member of this event.",
        )

    if event.ends_at and datetime.now(timezone.utc) >= event.ends_at:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can no longer leave an event after it has ended.",
        )

    indexing_status = event.indexing_status

    if indexing_status == EventProcessingStatus.IN_PROGRESS:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Event indexing is still in progress. Please try leaving again shortly.",
        )

    if indexing_status == EventProcessingStatus.FAILED:
        # Short grace period for eventual consistency in status propagation.
        await asyncio.sleep(5)
        refreshed_event = await event_dal.get_by_id(event_id)
        if refreshed_event:
            indexing_status = refreshed_event.indexing_status

    if indexing_status == EventProcessingStatus.COMPLETED:
        collection_id = build_event_collection_id(event_id)
        try:
            RekognitionService().delete_faces_by_user(
                collection_id=collection_id,
                user_id=current_user.id,
            )
        except RekognitionError as exc:
            logger.error(
                "Failed to delete faces for user=%s event=%s before leave: %s",
                current_user.id,
                event_id,
                exc,
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to remove user face data from event collection.",
            ) from exc

    # Delete consent first (foreign key reference)
    await consent_dal.delete(event_id, current_user.id)

    # Delete membership
    deleted = await membership_dal.leave_event(event_id, current_user.id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You are not a member of this event.",
        )
