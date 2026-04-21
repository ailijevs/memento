"""Tests for PATCH /api/v1/profiles/me/notification-preferences."""

import os
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

os.environ["DEBUG"] = "false"

from app.api.profiles import get_notification_dal  # noqa: E402
from app.auth import CurrentUser, get_current_user  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture
def client():
    """Create a test client with isolated dependency overrides."""
    app.dependency_overrides.clear()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _mock_user(user_id: UUID) -> CurrentUser:
    return CurrentUser(id=user_id, email="test@example.com", access_token="test-token")


def test_update_notification_preferences_success(client: TestClient):
    user_id = uuid4()
    now = datetime.now(timezone.utc)

    notification_dal = SimpleNamespace(
        upsert_preferences=AsyncMock(
            return_value=SimpleNamespace(
                user_id=user_id,
                email_notifications=True,
                event_updates=False,
                host_messages=True,
                created_at=now,
                updated_at=now,
            )
        )
    )

    app.dependency_overrides[get_current_user] = lambda: _mock_user(user_id)
    app.dependency_overrides[get_notification_dal] = lambda: notification_dal

    response = client.patch(
        "/api/v1/profiles/me/notification-preferences",
        json={"event_updates": False},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == str(user_id)
    assert data["event_updates"] is False
    notification_dal.upsert_preferences.assert_awaited_once()


def test_update_notification_preferences_rejects_empty_payload(client: TestClient):
    user_id = uuid4()
    notification_dal = SimpleNamespace(upsert_preferences=AsyncMock())

    app.dependency_overrides[get_current_user] = lambda: _mock_user(user_id)
    app.dependency_overrides[get_notification_dal] = lambda: notification_dal

    response = client.patch(
        "/api/v1/profiles/me/notification-preferences",
        json={},
    )

    assert response.status_code == 400
    assert "At least one preference field must be provided." in response.json()["detail"]
    notification_dal.upsert_preferences.assert_not_awaited()
