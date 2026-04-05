"""API endpoints for events."""

import asyncio
import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import CurrentUser, get_current_user
from app.dals import EventDAL
from app.db import get_supabase_client
from app.schemas import EventCreate, EventProcessingStatus, EventResponse, EventUpdate
from app.services.rekognition import RekognitionError, RekognitionService
from app.utils.rekognition_helpers import build_event_collection_id

router = APIRouter(prefix="/events", tags=["events"])
logger = logging.getLogger(__name__)


def get_event_dal(current_user: Annotated[CurrentUser, Depends(get_current_user)]) -> EventDAL:
    """Dependency to get EventDAL with authenticated client."""
    client = get_supabase_client(current_user.access_token)
    return EventDAL(client)


@router.get("/me", response_model=list[EventResponse])
async def list_my_events(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    dal: Annotated[EventDAL, Depends(get_event_dal)],
) -> list[EventResponse]:
    """Get all events the current user is a member of."""
    return await dal.get_user_events(current_user.id)


@router.get("/organized", response_model=list[EventResponse])
async def list_my_organized_events(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    dal: Annotated[EventDAL, Depends(get_event_dal)],
) -> list[EventResponse]:
    """Get all not-yet-ended events organized by the current user."""
    return await dal.get_organized_events(current_user.id)


@router.get("", response_model=list[EventResponse])
async def list_events(
    dal: Annotated[EventDAL, Depends(get_event_dal)],
) -> list[EventResponse]:
    """Get all active events visible to the current user."""
    return await dal.get_active_events()


@router.post("", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def create_event(
    data: EventCreate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    dal: Annotated[EventDAL, Depends(get_event_dal)],
) -> EventResponse:
    """Create a new event. The current user becomes the creator."""
    if not data.name.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Event name is required.",
        )

    duplicate_exists = await dal.exists_duplicate(
        name=data.name,
        starts_at=data.starts_at,
        ends_at=data.ends_at,
        location=data.location,
        created_by=current_user.id,
    )
    if duplicate_exists:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An event with the same info already exists.",
        )

    return await dal.create(current_user.id, data)


@router.patch("/{event_id}", response_model=EventResponse)
async def update_event(
    event_id: UUID,
    data: EventUpdate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    dal: Annotated[EventDAL, Depends(get_event_dal)],
) -> EventResponse:
    """
    Update an event.
    RLS enforces: only the creator can update.
    """
    existing = await dal.get_by_id(event_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found or you don't have permission to update.",
        )

    merged_name = data.name if data.name is not None else existing.name
    merged_starts_at = data.starts_at if data.starts_at is not None else existing.starts_at
    merged_ends_at = data.ends_at if data.ends_at is not None else existing.ends_at
    merged_location = data.location if data.location is not None else existing.location

    duplicate_exists = await dal.exists_duplicate(
        name=merged_name,
        starts_at=merged_starts_at,
        ends_at=merged_ends_at,
        location=merged_location,
        created_by=current_user.id,
        exclude_event_id=event_id,
    )
    if duplicate_exists:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An event with the same info already exists.",
        )

    event = await dal.update(event_id, data)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found or you don't have permission to update.",
        )
    return event


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(
    event_id: UUID,
    dal: Annotated[EventDAL, Depends(get_event_dal)],
) -> None:
    """
    Soft delete an event (sets is_active=False).
    RLS enforces: only the creator can delete.
    """
    event = await dal.get_by_id(event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found or you don't have permission to delete.",
        )

    indexing_status = event.indexing_status

    if indexing_status == EventProcessingStatus.IN_PROGRESS:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Event indexing is still in progress. Please try deleting again shortly.",
        )

    if indexing_status == EventProcessingStatus.FAILED:
        # Short grace period for eventual consistency in status propagation.
        await asyncio.sleep(5)
        refreshed_event = await dal.get_by_id(event_id)
        if refreshed_event:
            indexing_status = refreshed_event.indexing_status

    if indexing_status == EventProcessingStatus.COMPLETED:
        collection_id = build_event_collection_id(event_id)
        try:
            RekognitionService().delete_collection(collection_id=collection_id)
        except (RekognitionError, RuntimeError) as exc:
            logger.error("Failed to delete face collection for event=%s: %s", event_id, exc)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to delete event face collection.",
            ) from exc

    deleted = await dal.delete(event_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found or you don't have permission to delete.",
        )
