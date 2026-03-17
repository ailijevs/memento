"""API endpoints for event consents."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import CurrentUser, get_current_user
from app.dals import ConsentDAL
from app.db import get_supabase_client
from app.schemas import ConsentResponse, ConsentUpdate

router = APIRouter(tags=["events"])


def get_consent_dal(current_user: Annotated[CurrentUser, Depends(get_current_user)]) -> ConsentDAL:
    """Dependency to get ConsentDAL with authenticated client."""
    client = get_supabase_client(current_user.access_token)
    return ConsentDAL(client)


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
    dal: Annotated[ConsentDAL, Depends(get_consent_dal)],
) -> ConsentResponse:
    """
    Update consent settings for an event.
    Timestamps are automatically managed:
    - consented_at is set when granting consent
    - revoked_at is set when revoking consent
    """
    consent = await dal.update(event_id, current_user.id, data)
    if not consent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Consent not found. Are you a member of this event?",
        )
    return consent
