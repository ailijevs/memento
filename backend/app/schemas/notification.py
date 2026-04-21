"""Pydantic schemas for notifications and notification preferences."""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict


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
