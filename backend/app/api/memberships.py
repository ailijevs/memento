"""API endpoints for event memberships."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import CurrentUser, get_current_user
from app.db import get_supabase_client
from app.dals import ConsentDAL, MembershipDAL
from app.schemas import (
    ConsentCreate,
    MembershipCreate,
    MembershipResponse,
    MembershipUpdate,
)

router = APIRouter(prefix="/memberships", tags=["memberships"])


def get_membership_dal(
    current_user: Annotated[CurrentUser, Depends(get_current_user)]
) -> MembershipDAL:
    """Dependency to get MembershipDAL with authenticated client."""
    client = get_supabase_client(current_user.access_token)
    return MembershipDAL(client)


def get_consent_dal(
    current_user: Annotated[CurrentUser, Depends(get_current_user)]
) -> ConsentDAL:
    """Dependency to get ConsentDAL with authenticated client."""
    client = get_supabase_client(current_user.access_token)
    return ConsentDAL(client)


@router.get("/", response_model=list[MembershipResponse])
async def list_my_memberships(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    dal: Annotated[MembershipDAL, Depends(get_membership_dal)],
) -> list[MembershipResponse]:
    """Get all events the current user is a member of."""
    return await dal.get_user_memberships(current_user.id)


@router.post("/join", response_model=MembershipResponse, status_code=status.HTTP_201_CREATED)
async def join_event(
    data: MembershipCreate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    membership_dal: Annotated[MembershipDAL, Depends(get_membership_dal)],
    consent_dal: Annotated[ConsentDAL, Depends(get_consent_dal)],
) -> MembershipResponse:
    """
    Join an event. Creates both membership and consent records.
    Consent defaults to False (explicit opt-in required).
    """
    # Check if already a member
    existing = await membership_dal.get(data.event_id, current_user.id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You are already a member of this event.",
        )

    # Create membership
    membership = await membership_dal.join_event(current_user.id, data)

    # Create default consent (both False)
    await consent_dal.create(
        current_user.id,
        ConsentCreate(
            event_id=data.event_id,
            allow_profile_display=False,
            allow_recognition=False,
        ),
    )

    return membership


@router.get("/event/{event_id}", response_model=list[MembershipResponse])
async def list_event_members(
    event_id: UUID,
    dal: Annotated[MembershipDAL, Depends(get_membership_dal)],
) -> list[MembershipResponse]:
    """
    Get all members of an event.
    RLS enforces: only visible if caller is also a member.
    """
    return await dal.get_event_members(event_id)


@router.get("/event/{event_id}/me", response_model=MembershipResponse)
async def get_my_membership(
    event_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    dal: Annotated[MembershipDAL, Depends(get_membership_dal)],
) -> MembershipResponse:
    """Get the current user's membership for a specific event."""
    membership = await dal.get(event_id, current_user.id)
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You are not a member of this event.",
        )
    return membership


@router.patch("/event/{event_id}/me", response_model=MembershipResponse)
async def update_my_membership(
    event_id: UUID,
    data: MembershipUpdate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    dal: Annotated[MembershipDAL, Depends(get_membership_dal)],
) -> MembershipResponse:
    """Update the current user's membership for an event."""
    membership = await dal.update(event_id, current_user.id, data)
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You are not a member of this event.",
        )
    return membership


@router.post("/event/{event_id}/check-in", response_model=MembershipResponse)
async def check_in_to_event(
    event_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    dal: Annotated[MembershipDAL, Depends(get_membership_dal)],
) -> MembershipResponse:
    """Check in to an event. Sets checked_in_at timestamp."""
    membership = await dal.check_in(event_id, current_user.id)
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You are not a member of this event.",
        )
    return membership


@router.delete("/event/{event_id}/leave", status_code=status.HTTP_204_NO_CONTENT)
async def leave_event(
    event_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    membership_dal: Annotated[MembershipDAL, Depends(get_membership_dal)],
    consent_dal: Annotated[ConsentDAL, Depends(get_consent_dal)],
) -> None:
    """
    Leave an event. Deletes both membership and consent records.
    """
    # Delete consent first (foreign key reference)
    await consent_dal.delete(event_id, current_user.id)

    # Delete membership
    deleted = await membership_dal.leave_event(event_id, current_user.id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You are not a member of this event.",
        )
