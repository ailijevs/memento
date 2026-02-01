"""Pydantic schemas for event consents."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ConsentBase(BaseModel):
    """Base consent fields."""

    allow_profile_display: bool = False
    allow_recognition: bool = False


class ConsentCreate(ConsentBase):
    """Schema for creating consent (when joining an event)."""

    event_id: UUID


class ConsentUpdate(BaseModel):
    """Schema for updating consent preferences."""

    allow_profile_display: bool | None = None
    allow_recognition: bool | None = None


class ConsentResponse(ConsentBase):
    """Schema for consent responses."""

    event_id: UUID
    user_id: UUID
    consented_at: datetime | None = None
    revoked_at: datetime | None = None
    updated_at: datetime

    class Config:
        from_attributes = True
