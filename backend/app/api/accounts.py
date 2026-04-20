"""Account-level API endpoints (e.g. self-service deletion)."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client

from app.auth import CurrentUser, get_current_user
from app.db import get_admin_client
from app.services.account_deletion import delete_current_account

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_account(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    admin: Annotated[Client, Depends(get_admin_client)],
) -> None:
    """
    Permanently delete the current user's account.

    Removes events they created (and related data), profile photo in Storage,
    then deletes the Supabase Auth user (cascading profile, memberships, consents).
    """
    try:
        delete_current_account(admin=admin, user_id=current_user.id)
    except Exception as exc:
        logger.exception("Account deletion failed for user_id=%s", current_user.id)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not complete account deletion. Please try again or contact support.",
        ) from exc
