"""Tests for notification service behavior."""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from app.config import Settings
from app.schemas import EventProcessingStatus, EventResponse, NotificationType
from app.services.notification import NotificationRecipient, NotificationService


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


def test_should_send_for_start_time_change():
    """Start-time changes should trigger update emails."""
    old_event = _event()
    new_event = old_event.model_copy(update={"starts_at": old_event.starts_at + timedelta(hours=1)})

    should_send, reasons = _service().should_send_event_update(
        old_event=old_event,
        new_event=new_event,
    )

    assert should_send is True
    assert "start_time" in reasons
    assert "end_time" not in reasons


def test_should_send_for_end_time_change():
    """End-time changes should trigger update emails."""
    old_event = _event()
    new_event = old_event.model_copy(update={"ends_at": old_event.ends_at + timedelta(hours=1)})

    should_send, reasons = _service().should_send_event_update(
        old_event=old_event,
        new_event=new_event,
    )

    assert should_send is True
    assert "end_time" in reasons
    assert "start_time" not in reasons


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


def test_filter_opted_in_user_ids_uses_host_message_preferences():
    """Host-message delivery should honor the host_messages preference flag."""
    service = _service()
    user_ids = [uuid4(), uuid4()]
    service.notification_dal.get_host_message_opt_in_user_ids = AsyncMock(
        return_value={user_ids[0]}
    )

    opted_in_user_ids = asyncio.run(
        service._filter_opted_in_user_ids(
            user_ids=user_ids,
            notification_type=NotificationType.HOST_MESSAGE,
        )
    )

    assert opted_in_user_ids == [user_ids[0]]
    service.notification_dal.get_host_message_opt_in_user_ids.assert_awaited_once_with(user_ids)


def test_build_host_message_email_body_renders_message_and_event_details():
    """Host-message emails should include the attendee message and event metadata."""
    service = _service()
    event = _event(location="Main Hall")

    body = service._build_host_message_email_body(
        event=event,
        message="Please arrive 15 minutes early.\nBring your badge.",
        actor_email="host@example.com",
    )

    assert "Please arrive 15 minutes early." in body
    assert "Bring your badge." in body
    assert event.name in body
    assert "Main Hall" in body
    assert "host@example.com" in body


def test_send_and_log_emits_info_log_on_success(caplog):
    """Successful sends should emit an info log entry."""
    service = _service()
    recipient = NotificationRecipient(user_id=uuid4(), email="member@example.com")
    event_id = uuid4()
    service._send_email = AsyncMock(return_value=True)
    service._log_notification = AsyncMock()

    with caplog.at_level(logging.INFO, logger="app.services.notification"):
        asyncio.run(
            service._send_and_log(
                recipients=[recipient],
                subject="Subject",
                body="<p>Hello</p>",
                event_id=event_id,
                notification_type=NotificationType.HOST_MESSAGE,
            )
        )

    assert (
        f"Notification email sent to user={recipient.user_id} email={recipient.email} "
        f"type=host_message event={event_id}"
    ) in caplog.text
