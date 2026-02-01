"""API endpoints for event consents."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import CurrentUser, get_current_user
from app.db import get_supabase_client
from app.dals import ConsentDAL
from app.schemas import ConsentResponse, ConsentUpdate

router = APIRouter(prefix="/consents", tags=["consents"])


def get_consent_dal(
    current_user: Annotated[CurrentUser, Depends(get_current_user)]
) -> ConsentDAL:
    """Dependency to get ConsentDAL with authenticated client."""
    client = get_supabase_client(current_user.access_token)
    return ConsentDAL(client)


@router.get("/", response_model=list[ConsentResponse])
async def list_my_consents(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    dal: Annotated[ConsentDAL, Depends(get_consent_dal)],
) -> list[ConsentResponse]:
    """Get all consent settings for the current user across all events."""
    return await dal.get_user_consents(current_user.id)


@router.get("/event/{event_id}", response_model=ConsentResponse)
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


@router.patch("/event/{event_id}", response_model=ConsentResponse)
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


@router.post("/event/{event_id}/grant-all", response_model=ConsentResponse)
async def grant_all_consents(
    event_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    dal: Annotated[ConsentDAL, Depends(get_consent_dal)],
) -> ConsentResponse:
    """Grant all consent permissions for an event."""
    consent = await dal.grant_all(event_id, current_user.id)
    if not consent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Consent not found. Are you a member of this event?",
        )
    return consent


@router.post("/event/{event_id}/revoke-all", response_model=ConsentResponse)
async def revoke_all_consents(
    event_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    dal: Annotated[ConsentDAL, Depends(get_consent_dal)],
) -> ConsentResponse:
    """
    Revoke all consent permissions for an event.
    This is a privacy-first action that immediately hides the user
    from the event directory and disables face recognition.
    """
    consent = await dal.revoke_all(event_id, current_user.id)
    if not consent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Consent not found. Are you a member of this event?",
        )
    return consent
