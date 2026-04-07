"""Tests for PATCH /api/v1/events/{event_id}/consents/me behavior."""

import os
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

os.environ["DEBUG"] = "false"

from app.api.consents import (  # noqa: E402
    get_consent_dal,
    get_event_dal,
    get_profile_dal,
)
from app.auth import CurrentUser, get_current_user  # noqa: E402
from app.main import app  # noqa: E402
from app.schemas import ConsentResponse, EventProcessingStatus  # noqa: E402


@pytest.fixture
def client():
    """Create a test client with isolated dependency overrides."""
    app.dependency_overrides.clear()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _mock_user(user_id: UUID) -> CurrentUser:
    """Build a mock authenticated user."""
    return CurrentUser(id=user_id, email="test@example.com", access_token="test-token")


def _consent(
    event_id: UUID,
    user_id: UUID,
    allow_profile_display: bool,
    allow_recognition: bool,
):
    """Build a consent response fixture payload."""
    return ConsentResponse(
        event_id=event_id,
        user_id=user_id,
        allow_profile_display=allow_profile_display,
        allow_recognition=allow_recognition,
        consented_at=None,
        revoked_at=None,
        updated_at=datetime.now(timezone.utc),
    )


def _event(*, created_by: UUID, ends_at: datetime, indexing_status: EventProcessingStatus):
    """Build an event-like object used by endpoint logic."""
    return SimpleNamespace(
        created_by=created_by,
        ends_at=ends_at,
        indexing_status=indexing_status,
    )


def test_update_consent_ended_event_returns_403(client: TestClient):
    """Reject updates once the event has ended."""
    event_id = uuid4()
    user_id = uuid4()
    event_dal = SimpleNamespace(
        get_by_id=AsyncMock(
            return_value=_event(
                created_by=user_id,
                ends_at=datetime.now(timezone.utc) - timedelta(minutes=1),
                indexing_status=EventProcessingStatus.PENDING,
            )
        )
    )
    consent_dal = SimpleNamespace(get=AsyncMock(), update=AsyncMock())
    profile_dal = SimpleNamespace(get_by_user_id=AsyncMock())

    app.dependency_overrides[get_current_user] = lambda: _mock_user(user_id)
    app.dependency_overrides[get_event_dal] = lambda: event_dal
    app.dependency_overrides[get_consent_dal] = lambda: consent_dal
    app.dependency_overrides[get_profile_dal] = lambda: profile_dal

    response = client.patch(
        f"/api/v1/events/{event_id}/consents/me",
        json={"allow_profile_display": True},
    )

    assert response.status_code == 403
    assert "can no longer be updated" in response.json()["detail"]
    consent_dal.get.assert_not_awaited()
    consent_dal.update.assert_not_awaited()


def test_update_consent_toggle_recognition_in_progress_returns_409(client: TestClient):
    """Reject recognition toggles while indexing is in progress."""
    event_id = uuid4()
    user_id = uuid4()
    event_dal = SimpleNamespace(
        get_by_id=AsyncMock(
            return_value=_event(
                created_by=uuid4(),
                ends_at=datetime.now(timezone.utc) + timedelta(hours=1),
                indexing_status=EventProcessingStatus.IN_PROGRESS,
            )
        )
    )
    consent_dal = SimpleNamespace(
        get=AsyncMock(return_value=_consent(event_id, user_id, False, False)),
        update=AsyncMock(),
    )
    profile_dal = SimpleNamespace(get_by_user_id=AsyncMock())

    app.dependency_overrides[get_current_user] = lambda: _mock_user(user_id)
    app.dependency_overrides[get_event_dal] = lambda: event_dal
    app.dependency_overrides[get_consent_dal] = lambda: consent_dal
    app.dependency_overrides[get_profile_dal] = lambda: profile_dal

    response = client.patch(
        f"/api/v1/events/{event_id}/consents/me",
        json={"allow_recognition": True},
    )

    assert response.status_code == 409
    assert "indexing is in progress" in response.json()["detail"]
    consent_dal.update.assert_not_awaited()


def test_update_consent_toggle_recognition_completed_off_deletes_face_then_updates(
    client: TestClient,
):
    """When disabling recognition post-indexing, remove faces before DB update."""
    event_id = uuid4()
    user_id = uuid4()
    event_dal = SimpleNamespace(
        get_by_id=AsyncMock(
            return_value=_event(
                created_by=uuid4(),
                ends_at=datetime.now(timezone.utc) + timedelta(hours=1),
                indexing_status=EventProcessingStatus.COMPLETED,
            )
        )
    )
    updated = _consent(event_id, user_id, False, False)
    consent_dal = SimpleNamespace(
        get=AsyncMock(return_value=_consent(event_id, user_id, False, True)),
        update=AsyncMock(return_value=updated),
    )
    profile_dal = SimpleNamespace(get_by_user_id=AsyncMock())
    rekognition_instance = MagicMock()

    app.dependency_overrides[get_current_user] = lambda: _mock_user(user_id)
    app.dependency_overrides[get_event_dal] = lambda: event_dal
    app.dependency_overrides[get_consent_dal] = lambda: consent_dal
    app.dependency_overrides[get_profile_dal] = lambda: profile_dal

    with patch("app.api.consents.RekognitionService", return_value=rekognition_instance):
        response = client.patch(
            f"/api/v1/events/{event_id}/consents/me",
            json={"allow_recognition": False},
        )

    assert response.status_code == 200
    assert response.json()["allow_recognition"] is False
    rekognition_instance.delete_faces_by_user.assert_called_once()
    consent_dal.update.assert_awaited_once()


def test_update_consent_toggle_recognition_completed_on_requires_photo(client: TestClient):
    """Enabling recognition requires an uploaded profile photo."""
    event_id = uuid4()
    user_id = uuid4()
    event_dal = SimpleNamespace(
        get_by_id=AsyncMock(
            return_value=_event(
                created_by=uuid4(),
                ends_at=datetime.now(timezone.utc) + timedelta(hours=1),
                indexing_status=EventProcessingStatus.COMPLETED,
            )
        )
    )
    consent_dal = SimpleNamespace(
        get=AsyncMock(return_value=_consent(event_id, user_id, False, False)),
        update=AsyncMock(),
    )
    profile_dal = SimpleNamespace(get_by_user_id=AsyncMock(return_value=None))
    rekognition_instance = MagicMock()

    app.dependency_overrides[get_current_user] = lambda: _mock_user(user_id)
    app.dependency_overrides[get_event_dal] = lambda: event_dal
    app.dependency_overrides[get_consent_dal] = lambda: consent_dal
    app.dependency_overrides[get_profile_dal] = lambda: profile_dal

    with patch("app.api.consents.RekognitionService", return_value=rekognition_instance):
        response = client.patch(
            f"/api/v1/events/{event_id}/consents/me",
            json={"allow_recognition": True},
        )

    assert response.status_code == 400
    assert "profile photo is required" in response.json()["detail"]
    rekognition_instance.index_face_from_s3.assert_not_called()
    consent_dal.update.assert_not_awaited()


def test_update_consent_toggle_recognition_completed_on_indexes_face_then_updates(
    client: TestClient,
):
    """When enabling recognition post-indexing, index face before DB update."""
    event_id = uuid4()
    user_id = uuid4()
    event_dal = SimpleNamespace(
        get_by_id=AsyncMock(
            return_value=_event(
                created_by=uuid4(),
                ends_at=datetime.now(timezone.utc) + timedelta(hours=1),
                indexing_status=EventProcessingStatus.COMPLETED,
            )
        )
    )
    updated = _consent(event_id, user_id, True, True)
    consent_dal = SimpleNamespace(
        get=AsyncMock(return_value=_consent(event_id, user_id, False, False)),
        update=AsyncMock(return_value=updated),
    )
    profile_dal = SimpleNamespace(
        get_by_user_id=AsyncMock(return_value=SimpleNamespace(photo_path="profiles/u1.jpg"))
    )
    rekognition_instance = MagicMock()

    app.dependency_overrides[get_current_user] = lambda: _mock_user(user_id)
    app.dependency_overrides[get_event_dal] = lambda: event_dal
    app.dependency_overrides[get_consent_dal] = lambda: consent_dal
    app.dependency_overrides[get_profile_dal] = lambda: profile_dal

    with (
        patch("app.api.consents.RekognitionService", return_value=rekognition_instance),
        patch(
            "app.api.consents.get_settings",
            return_value=SimpleNamespace(s3_bucket_name="test-bucket"),
        ),
    ):
        response = client.patch(
            f"/api/v1/events/{event_id}/consents/me",
            json={"allow_recognition": True},
        )

    assert response.status_code == 200
    assert response.json()["allow_recognition"] is True
    rekognition_instance.index_face_from_s3.assert_called_once()
    consent_dal.update.assert_awaited_once()


def test_update_consent_toggle_recognition_pending_updates_without_rekognition(
    client: TestClient,
):
    """Before indexing completes, recognition toggle should only update consent row."""
    event_id = uuid4()
    user_id = uuid4()
    event_dal = SimpleNamespace(
        get_by_id=AsyncMock(
            return_value=_event(
                created_by=uuid4(),
                ends_at=datetime.now(timezone.utc) + timedelta(hours=1),
                indexing_status=EventProcessingStatus.PENDING,
            )
        )
    )
    updated = _consent(event_id, user_id, False, True)
    consent_dal = SimpleNamespace(
        get=AsyncMock(return_value=_consent(event_id, user_id, False, False)),
        update=AsyncMock(return_value=updated),
    )
    profile_dal = SimpleNamespace(get_by_user_id=AsyncMock())
    rekognition_instance = MagicMock()

    app.dependency_overrides[get_current_user] = lambda: _mock_user(user_id)
    app.dependency_overrides[get_event_dal] = lambda: event_dal
    app.dependency_overrides[get_consent_dal] = lambda: consent_dal
    app.dependency_overrides[get_profile_dal] = lambda: profile_dal

    with patch("app.api.consents.RekognitionService", return_value=rekognition_instance):
        response = client.patch(
            f"/api/v1/events/{event_id}/consents/me",
            json={"allow_recognition": True},
        )

    assert response.status_code == 200
    assert response.json()["allow_recognition"] is True
    rekognition_instance.index_face_from_s3.assert_not_called()
    rekognition_instance.delete_faces_by_user.assert_not_called()
    consent_dal.update.assert_awaited_once()
