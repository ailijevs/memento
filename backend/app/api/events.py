"""API endpoints for events."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import get_current_user, CurrentUser
from app.db import get_supabase_client
from app.dals import EventDAL
from app.schemas import EventCreate, EventUpdate, EventResponse

router = APIRouter(prefix="/events", tags=["events"])


def get_event_dal(current_user: Annotated[CurrentUser, Depends(get_current_user)]) -> EventDAL:
    """Dependency to get EventDAL with authenticated client."""
    client = get_supabase_client(current_user.access_token)
    return EventDAL(client)


@router.get("/", response_model=list[EventResponse])
async def list_my_events(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    dal: Annotated[EventDAL, Depends(get_event_dal)],
) -> list[EventResponse]:
    """Get all events the current user is a member of."""
    return await dal.get_user_events(current_user.id)


@router.post("/", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def create_event(
    data: EventCreate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    dal: Annotated[EventDAL, Depends(get_event_dal)],
) -> EventResponse:
    """Create a new event. The current user becomes the creator."""
    return await dal.create(current_user.id, data)


@router.get("/{event_id}", response_model=EventResponse)
async def get_event(
    event_id: UUID,
    dal: Annotated[EventDAL, Depends(get_event_dal)],
) -> EventResponse:
    """
    Get event details.
    RLS enforces: only visible if user is creator or member.
    """
    event = await dal.get_by_id(event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found or not accessible.",
        )
    return event


@router.patch("/{event_id}", response_model=EventResponse)
async def update_event(
    event_id: UUID,
    data: EventUpdate,
    dal: Annotated[EventDAL, Depends(get_event_dal)],
) -> EventResponse:
    """
    Update an event.
    RLS enforces: only the creator can update.
    """
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
    deleted = await dal.delete(event_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found or you don't have permission to delete.",
        )
