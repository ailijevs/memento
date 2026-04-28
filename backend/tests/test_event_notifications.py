"""Tests for event notification dispatch behavior in events API."""

import os
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

os.environ["DEBUG"] = "false"

import app.api.events as events_api  # noqa: E402
from app.api.events import get_event_dal as get_events_event_dal  # noqa: E402
from app.auth import CurrentUser, get_current_user  # noqa: E402
from app.main import app  # noqa: E402
from app.schemas import EventProcessingStatus, EventResponse  # noqa: E402
from app.services.notification import NotificationRecipient  # noqa: E402


@pytest.fixture
def client():
    """Create a test client with isolated dependency overrides."""
    app.dependency_overrides.clear()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _mock_user(user_id: UUID) -> CurrentUser:
    return CurrentUser(id=user_id, email="test@example.com", access_token="test-token")


def _event_response(
    *,
    event_id: UUID,
    created_by: UUID,
    location: str,
    starts_at: datetime,
    ends_at: datetime,
    is_active: bool = True,
) -> EventResponse:
    return EventResponse(
        event_id=event_id,
        name="Networking Night",
        starts_at=starts_at,
        ends_at=ends_at,
        location=location,
        description="desc",
        max_participants=30,
        is_active=is_active,
        created_by=created_by,
        created_at=datetime.now(timezone.utc),
        indexing_status=EventProcessingStatus.PENDING,
        cleanup_status=EventProcessingStatus.PENDING,
    )


def test_update_event_dispatches_notifications_in_background(client: TestClient, monkeypatch):
    """PATCH should queue and run update notification logic via background task."""
    event_id = uuid4()
    user_id = uuid4()
    starts_at = datetime.now(timezone.utc) + timedelta(days=1)
    ends_at = starts_at + timedelta(hours=2)

    old_event = _event_response(
        event_id=event_id,
        created_by=user_id,
        location="Room 101",
        starts_at=starts_at,
        ends_at=ends_at,
    )
    updated_event = old_event.model_copy(update={"location": "Room 202"})

    event_dal = SimpleNamespace(
        get_by_id=AsyncMock(return_value=old_event),
        exists_duplicate=AsyncMock(return_value=False),
        update=AsyncMock(return_value=updated_event),
    )
    notification_service = SimpleNamespace(
        notify_event_updated=AsyncMock(),
    )

    monkeypatch.setattr(events_api, "NotificationService", lambda: notification_service)
    app.dependency_overrides[get_current_user] = lambda: _mock_user(user_id)
    app.dependency_overrides[get_events_event_dal] = lambda: event_dal

    response = client.patch(
        f"/api/v1/events/{event_id}",
        json={"location": "Room 202"},
    )

    assert response.status_code == 200
    event_dal.update.assert_awaited_once()
    notification_service.notify_event_updated.assert_awaited_once_with(
        old_event=old_event,
        new_event=updated_event,
        actor_user_id=user_id,
    )


def test_update_event_succeeds_when_background_notification_fails(
    client: TestClient,
    monkeypatch,
):
    """PATCH response should still succeed if notification sending raises."""
    event_id = uuid4()
    user_id = uuid4()
    starts_at = datetime.now(timezone.utc) + timedelta(days=1)
    ends_at = starts_at + timedelta(hours=2)

    old_event = _event_response(
        event_id=event_id,
        created_by=user_id,
        location="Room 101",
        starts_at=starts_at,
        ends_at=ends_at,
    )
    updated_event = old_event.model_copy(update={"location": "Room 202"})

    event_dal = SimpleNamespace(
        get_by_id=AsyncMock(return_value=old_event),
        exists_duplicate=AsyncMock(return_value=False),
        update=AsyncMock(return_value=updated_event),
    )
    notification_service = SimpleNamespace(
        notify_event_updated=AsyncMock(side_effect=RuntimeError("send failed")),
    )

    monkeypatch.setattr(events_api, "NotificationService", lambda: notification_service)
    app.dependency_overrides[get_current_user] = lambda: _mock_user(user_id)
    app.dependency_overrides[get_events_event_dal] = lambda: event_dal

    response = client.patch(
        f"/api/v1/events/{event_id}",
        json={"location": "Room 202"},
    )

    assert response.status_code == 200
    notification_service.notify_event_updated.assert_awaited_once()


def test_delete_event_prefetches_recipients_and_dispatches_background_notification(
    client: TestClient,
    monkeypatch,
):
    """DELETE should pre-resolve recipients and pass them to background notifier."""
    event_id = uuid4()
    user_id = uuid4()
    recipient_id = uuid4()
    starts_at = datetime.now(timezone.utc) + timedelta(days=1)
    ends_at = starts_at + timedelta(hours=2)
    event = _event_response(
        event_id=event_id,
        created_by=user_id,
        location="Room 101",
        starts_at=starts_at,
        ends_at=ends_at,
    )

    recipients = [NotificationRecipient(user_id=recipient_id, email="attendee@example.com")]
    event_dal = SimpleNamespace(
        get_by_id=AsyncMock(return_value=event),
        delete=AsyncMock(return_value=True),
    )
    notification_service = SimpleNamespace(
        prepare_event_update_recipients=AsyncMock(return_value=recipients),
        notify_event_deleted=AsyncMock(),
    )

    monkeypatch.setattr(events_api, "NotificationService", lambda: notification_service)
    app.dependency_overrides[get_current_user] = lambda: _mock_user(user_id)
    app.dependency_overrides[get_events_event_dal] = lambda: event_dal

    response = client.delete(f"/api/v1/events/{event_id}")

    assert response.status_code == 204
    event_dal.delete.assert_awaited_once_with(event_id)
    notification_service.prepare_event_update_recipients.assert_awaited_once_with(
        event_id=event_id,
        actor_user_id=user_id,
    )
    notification_service.notify_event_deleted.assert_awaited_once_with(
        deleted_event=event,
        actor_user_id=user_id,
        recipients=recipients,
    )
