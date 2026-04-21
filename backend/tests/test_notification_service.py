"""Tests for event update notification decision logic."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock
from uuid import uuid4

from app.config import Settings
from app.schemas import EventProcessingStatus, EventResponse
from app.services.notification import NotificationService


def _event(
    *,
    starts_at: datetime | None = None,
    ends_at: datetime | None = None,
    location: str | None = "Room 101",
    is_active: bool = True,
    description: str | None = "Initial description",
) -> EventResponse:
    now = datetime.now(timezone.utc)
    return EventResponse(
        event_id=uuid4(),
        name="Networking Night",
        starts_at=starts_at or now + timedelta(hours=1),
        ends_at=ends_at or now + timedelta(hours=2),
        location=location,
        description=description,
        max_participants=50,
        is_active=is_active,
        created_by=uuid4(),
        created_at=now,
        indexing_status=EventProcessingStatus.PENDING,
        cleanup_status=EventProcessingStatus.PENDING,
    )


def _service() -> NotificationService:
    settings = Settings(
        supabase_url="https://example.supabase.co",
        supabase_anon_key="anon-key",
        supabase_service_role_key="service-role-key",
        supabase_jwt_secret="jwt-secret",
        mail_enabled=False,
    )
    return NotificationService(
        admin_client=MagicMock(),
        settings=settings,
    )


def test_should_not_send_for_non_notifiable_changes():
    """Description-only changes should not trigger update emails."""
    old_event = _event(description="Before")
    new_event = old_event.model_copy(update={"description": "After"})

    should_send, reasons = _service().should_send_event_update(
        old_event=old_event,
        new_event=new_event,
    )

    assert should_send is False
    assert reasons == []


def test_should_send_for_time_change():
    """Time changes should trigger update emails."""
    old_event = _event()
    new_event = old_event.model_copy(update={"starts_at": old_event.starts_at + timedelta(hours=1)})

    should_send, reasons = _service().should_send_event_update(
        old_event=old_event,
        new_event=new_event,
    )

    assert should_send is True
    assert "time" in reasons


def test_should_send_for_location_change():
    """Location changes should trigger update emails."""
    old_event = _event(location="Room 101")
    new_event = old_event.model_copy(update={"location": "Room 202"})

    should_send, reasons = _service().should_send_event_update(
        old_event=old_event,
        new_event=new_event,
    )

    assert should_send is True
    assert "location" in reasons


def test_should_send_for_archival_change():
    """Archiving an event should trigger update emails."""
    old_event = _event(is_active=True)
    new_event = old_event.model_copy(update={"is_active": False})

    should_send, reasons = _service().should_send_event_update(
        old_event=old_event,
        new_event=new_event,
    )

    assert should_send is True
    assert "archived" in reasons
