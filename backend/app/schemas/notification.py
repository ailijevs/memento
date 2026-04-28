"""Pydantic schemas for notifications and notification preferences."""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class NotificationType(str, Enum):
    """Supported notification categories."""

    EVENT_UPDATE = "event_update"
    HOST_MESSAGE = "host_message"


class NotificationStatus(str, Enum):
    """Delivery status for a notification attempt."""

    SENT = "sent"
    FAILED = "failed"


class NotificationLogCreate(BaseModel):
    """Schema for creating a notification log row."""

    user_id: UUID
    event_id: UUID | None = None
    type: NotificationType
    status: NotificationStatus


class NotificationLogResponse(BaseModel):
    """Schema for notification log rows."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    event_id: UUID | None = None
    type: NotificationType
    status: NotificationStatus
    created_at: datetime


class NotificationPreferenceResponse(BaseModel):
    """Schema for user notification preferences."""

    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    email_notifications: bool
    event_updates: bool
    host_messages: bool
    created_at: datetime
    updated_at: datetime


class NotificationPreferenceUpdate(BaseModel):
    """Schema for updating user notification preferences."""

    email_notifications: bool | None = None
    event_updates: bool | None = None
    host_messages: bool | None = None


class HostMessageRequest(BaseModel):
    """Schema for a host-sent message to event members."""

    subject: str = Field(..., min_length=1, max_length=160)
    message: str = Field(..., min_length=1, max_length=5000)

    @field_validator("subject", "message")
    @classmethod
    def not_blank(cls, value: str) -> str:
        """Reject values that are only whitespace."""
        if not value.strip():
            raise ValueError("must not be blank")
        return value


class HostMessageResponse(BaseModel):
    """Response for queued host-message delivery."""

    event_id: UUID
    recipient_count: int
    subject: str
    queued: bool = True
