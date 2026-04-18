"""Tests for event start/end time guards on delete/leave APIs."""

import os
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

os.environ["DEBUG"] = "false"

from app.api.events import get_event_dal as get_events_event_dal  # noqa: E402
from app.api.memberships import get_consent_dal as get_memberships_consent_dal  # noqa: E402
from app.api.memberships import get_event_dal as get_memberships_event_dal  # noqa: E402
from app.api.memberships import get_membership_dal as get_memberships_membership_dal  # noqa: E402
from app.auth import CurrentUser, get_current_user  # noqa: E402
from app.main import app  # noqa: E402
from app.schemas import EventProcessingStatus  # noqa: E402


@pytest.fixture
def client():
    """Create a test client with isolated dependency overrides."""
    app.dependency_overrides.clear()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _mock_user(user_id: UUID) -> CurrentUser:
    return CurrentUser(id=user_id, email="test@example.com", access_token="test-token")


def test_delete_event_blocked_after_start_time(client: TestClient):
    """Creators cannot delete events at/after start time."""
    event_id = uuid4()
    user_id = uuid4()

    event_dal = SimpleNamespace(
        get_by_id=AsyncMock(
            return_value=SimpleNamespace(
                starts_at=datetime.now(timezone.utc) - timedelta(minutes=1),
                indexing_status=EventProcessingStatus.PENDING,
            )
        ),
        delete=AsyncMock(),
    )

    app.dependency_overrides[get_current_user] = lambda: _mock_user(user_id)
    app.dependency_overrides[get_events_event_dal] = lambda: event_dal

    response = client.delete(f"/api/v1/events/{event_id}")

    assert response.status_code == 403
    assert "cannot be deleted after they have started" in response.json()["detail"]
    event_dal.delete.assert_not_awaited()


def test_leave_event_blocked_after_end_time(client: TestClient):
    """Attendees cannot leave events at/after end time."""
    event_id = uuid4()
    user_id = uuid4()

    event_dal = SimpleNamespace(
        get_by_id=AsyncMock(
            return_value=SimpleNamespace(
                ends_at=datetime.now(timezone.utc) - timedelta(minutes=1),
                indexing_status=EventProcessingStatus.PENDING,
            )
        )
    )
    membership_dal = SimpleNamespace(
        get=AsyncMock(return_value=SimpleNamespace(event_id=event_id, user_id=user_id)),
        leave_event=AsyncMock(),
    )
    consent_dal = SimpleNamespace(delete=AsyncMock())

    app.dependency_overrides[get_current_user] = lambda: _mock_user(user_id)
    app.dependency_overrides[get_memberships_event_dal] = lambda: event_dal
    app.dependency_overrides[get_memberships_membership_dal] = lambda: membership_dal
    app.dependency_overrides[get_memberships_consent_dal] = lambda: consent_dal

    response = client.delete(f"/api/v1/events/{event_id}/leave")

    assert response.status_code == 403
    assert "can no longer leave an event after it has ended" in response.json()["detail"]
    consent_dal.delete.assert_not_awaited()
    membership_dal.leave_event.assert_not_awaited()
