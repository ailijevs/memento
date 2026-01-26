"""Pydantic schemas for events."""
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, field_validator


class EventBase(BaseModel):
    """Base event fields."""

    name: str = Field(..., min_length=1, max_length=255)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    location: str | None = Field(None, max_length=500)
    is_active: bool = True

    @field_validator("ends_at")
    @classmethod
    def ends_after_starts(cls, v: datetime | None, info) -> datetime | None:
        """Validate that end time is after start time."""
        if v is not None and info.data.get("starts_at") is not None:
            if v <= info.data["starts_at"]:
                raise ValueError("ends_at must be after starts_at")
        return v


class EventCreate(EventBase):
    """Schema for creating a new event."""

    pass


class EventUpdate(BaseModel):
    """Schema for updating an event. All fields optional."""

    name: str | None = Field(None, min_length=1, max_length=255)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    location: str | None = Field(None, max_length=500)
    is_active: bool | None = None


class EventResponse(EventBase):
    """Schema for event responses."""

    event_id: UUID
    created_by: UUID
    created_at: datetime

    class Config:
        from_attributes = True
