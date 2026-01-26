"""Pydantic schemas for event memberships."""
from datetime import datetime
from enum import Enum
from uuid import UUID
from pydantic import BaseModel


class MembershipRole(str, Enum):
    """Membership role enum matching the database enum."""

    ATTENDEE = "attendee"
    ORGANIZER = "organizer"
    ADMIN = "admin"


class MembershipBase(BaseModel):
    """Base membership fields."""

    role: MembershipRole = MembershipRole.ATTENDEE


class MembershipCreate(MembershipBase):
    """Schema for creating a membership (joining an event)."""

    event_id: UUID


class MembershipUpdate(BaseModel):
    """Schema for updating a membership."""

    role: MembershipRole | None = None
    checked_in_at: datetime | None = None


class MembershipResponse(MembershipBase):
    """Schema for membership responses."""

    event_id: UUID
    user_id: UUID
    checked_in_at: datetime | None = None
    created_at: datetime

    class Config:
        from_attributes = True
