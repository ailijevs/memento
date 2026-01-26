"""API endpoints for user profiles."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import get_current_user, CurrentUser
from app.db import get_supabase_client
from app.dals import ProfileDAL
from app.schemas import (
    ProfileCreate,
    ProfileUpdate,
    ProfileResponse,
    ProfileDirectoryEntry,
)

router = APIRouter(prefix="/profiles", tags=["profiles"])


def get_profile_dal(current_user: Annotated[CurrentUser, Depends(get_current_user)]) -> ProfileDAL:
    """Dependency to get ProfileDAL with authenticated client."""
    client = get_supabase_client(current_user.access_token)
    return ProfileDAL(client)


@router.get("/me", response_model=ProfileResponse)
async def get_my_profile(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    dal: Annotated[ProfileDAL, Depends(get_profile_dal)],
) -> ProfileResponse:
    """Get the current user's profile."""
    profile = await dal.get_by_user_id(current_user.id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found. Please create one first.",
        )
    return profile


@router.post("/me", response_model=ProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_my_profile(
    data: ProfileCreate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    dal: Annotated[ProfileDAL, Depends(get_profile_dal)],
) -> ProfileResponse:
    """Create the current user's profile."""
    # Check if profile already exists
    existing = await dal.get_by_user_id(current_user.id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Profile already exists. Use PATCH to update.",
        )

    return await dal.create(current_user.id, data)


@router.patch("/me", response_model=ProfileResponse)
async def update_my_profile(
    data: ProfileUpdate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    dal: Annotated[ProfileDAL, Depends(get_profile_dal)],
) -> ProfileResponse:
    """Update the current user's profile."""
    profile = await dal.update(current_user.id, data)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found. Please create one first.",
        )
    return profile


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_profile(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    dal: Annotated[ProfileDAL, Depends(get_profile_dal)],
) -> None:
    """Delete the current user's profile."""
    deleted = await dal.delete(current_user.id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found.",
        )


@router.get("/{user_id}", response_model=ProfileResponse)
async def get_profile(
    user_id: UUID,
    dal: Annotated[ProfileDAL, Depends(get_profile_dal)],
) -> ProfileResponse:
    """
    Get another user's profile.
    RLS enforces: only visible if you share an event and they consented.
    """
    profile = await dal.get_by_user_id(user_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found or not visible.",
        )
    return profile


@router.get("/directory/{event_id}", response_model=list[ProfileDirectoryEntry])
async def get_event_directory(
    event_id: UUID,
    dal: Annotated[ProfileDAL, Depends(get_profile_dal)],
) -> list[ProfileDirectoryEntry]:
    """
    Get the directory of profiles for an event.
    Only returns profiles of users who have consented to display.
    Uses the get_event_directory SQL function.
    """
    return await dal.get_event_directory(event_id)
