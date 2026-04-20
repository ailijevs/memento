"""Tests for GET /api/v1/profiles/directory/{event_id} privacy behavior."""

import os
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

os.environ["DEBUG"] = "false"

from app.api.profiles import (  # noqa: E402
    get_consent_dal,
    get_event_dal,
    get_membership_dal,
    get_profile_dal,
)
from app.auth import CurrentUser, get_current_user  # noqa: E402
from app.main import app  # noqa: E402
from app.schemas.profile import ProfileDirectoryEntry  # noqa: E402


@pytest.fixture
def client():
    """Create a test client and isolate dependency overrides per test."""
    app.dependency_overrides.clear()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _mock_user(user_id: UUID) -> CurrentUser:
    return CurrentUser(id=user_id, email="test@example.com", access_token="test-token")


def _entry(user_id: UUID, full_name: str) -> ProfileDirectoryEntry:
    return ProfileDirectoryEntry(
        user_id=user_id,
        full_name=full_name,
        headline="",
        company=None,
        school=None,
        major=None,
        photo_path=None,
    )


def test_get_event_directory_404_when_event_not_found(client: TestClient):
    event_id = uuid4()
    user_id = uuid4()

    event_dal = SimpleNamespace(get_by_id=AsyncMock(return_value=None))
    membership_dal = SimpleNamespace(
        get=AsyncMock(),
        get_event_member_count=AsyncMock(),
    )
    consent_dal = SimpleNamespace(get=AsyncMock())
    profile_dal = SimpleNamespace(get_event_directory=AsyncMock())

    app.dependency_overrides[get_current_user] = lambda: _mock_user(user_id)
    app.dependency_overrides[get_event_dal] = lambda: event_dal
    app.dependency_overrides[get_membership_dal] = lambda: membership_dal
    app.dependency_overrides[get_consent_dal] = lambda: consent_dal
    app.dependency_overrides[get_profile_dal] = lambda: profile_dal

    response = client.get(f"/api/v1/profiles/directory/{event_id}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Event not found."
    membership_dal.get.assert_not_awaited()
    profile_dal.get_event_directory.assert_not_awaited()


def test_get_event_directory_404_when_user_not_creator_or_member(client: TestClient):
    event_id = uuid4()
    user_id = uuid4()
    creator_id = uuid4()

    event_dal = SimpleNamespace(
        get_by_id=AsyncMock(return_value=SimpleNamespace(created_by=creator_id))
    )
    membership_dal = SimpleNamespace(
        get=AsyncMock(return_value=None),
        get_event_member_count=AsyncMock(),
    )
    consent_dal = SimpleNamespace(get=AsyncMock())
    profile_dal = SimpleNamespace(get_event_directory=AsyncMock())

    app.dependency_overrides[get_current_user] = lambda: _mock_user(user_id)
    app.dependency_overrides[get_event_dal] = lambda: event_dal
    app.dependency_overrides[get_membership_dal] = lambda: membership_dal
    app.dependency_overrides[get_consent_dal] = lambda: consent_dal
    app.dependency_overrides[get_profile_dal] = lambda: profile_dal

    response = client.get(f"/api/v1/profiles/directory/{event_id}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Event not found or not accessible."
    membership_dal.get_event_member_count.assert_not_awaited()
    profile_dal.get_event_directory.assert_not_awaited()


def test_get_event_directory_creator_can_view_all_regardless_of_consent(client: TestClient):
    event_id = uuid4()
    creator_id = uuid4()
    attendee_id = uuid4()
    entries = [_entry(creator_id, "Creator User"), _entry(attendee_id, "Attendee User")]

    event_dal = SimpleNamespace(
        get_by_id=AsyncMock(return_value=SimpleNamespace(created_by=creator_id))
    )
    membership_dal = SimpleNamespace(
        get=AsyncMock(return_value=None),
        get_event_member_count=AsyncMock(return_value=2),
    )
    # Creator consent should not matter in this path.
    consent_dal = SimpleNamespace(
        get=AsyncMock(return_value=SimpleNamespace(allow_profile_display=False))
    )
    profile_dal = SimpleNamespace(get_event_directory=AsyncMock(return_value=entries))

    app.dependency_overrides[get_current_user] = lambda: _mock_user(creator_id)
    app.dependency_overrides[get_event_dal] = lambda: event_dal
    app.dependency_overrides[get_membership_dal] = lambda: membership_dal
    app.dependency_overrides[get_consent_dal] = lambda: consent_dal
    app.dependency_overrides[get_profile_dal] = lambda: profile_dal

    response = client.get(f"/api/v1/profiles/directory/{event_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["total_count"] == 2
    assert body["hidden_count"] == 0
    assert len(body["entries"]) == 2
    assert {item["user_id"] for item in body["entries"]} == {str(creator_id), str(attendee_id)}


def test_get_event_directory_member_with_consent_on_can_view_all(client: TestClient):
    event_id = uuid4()
    creator_id = uuid4()
    member_id = uuid4()
    other_id = uuid4()
    entries = [
        _entry(member_id, "Member User"),
        _entry(other_id, "Other User"),
    ]

    event_dal = SimpleNamespace(
        get_by_id=AsyncMock(return_value=SimpleNamespace(created_by=creator_id))
    )
    membership_dal = SimpleNamespace(
        get=AsyncMock(return_value=SimpleNamespace(event_id=event_id, user_id=member_id)),
        get_event_member_count=AsyncMock(return_value=2),
    )
    consent_dal = SimpleNamespace(
        get=AsyncMock(return_value=SimpleNamespace(allow_profile_display=True))
    )
    profile_dal = SimpleNamespace(get_event_directory=AsyncMock(return_value=entries))

    app.dependency_overrides[get_current_user] = lambda: _mock_user(member_id)
    app.dependency_overrides[get_event_dal] = lambda: event_dal
    app.dependency_overrides[get_membership_dal] = lambda: membership_dal
    app.dependency_overrides[get_consent_dal] = lambda: consent_dal
    app.dependency_overrides[get_profile_dal] = lambda: profile_dal

    response = client.get(f"/api/v1/profiles/directory/{event_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["total_count"] == 2
    assert body["hidden_count"] == 0
    assert len(body["entries"]) == 2


def test_get_event_directory_member_with_consent_off_sees_only_self(client: TestClient):
    event_id = uuid4()
    creator_id = uuid4()
    member_id = uuid4()
    other_id = uuid4()
    entries = [
        _entry(member_id, "Member User"),
        _entry(other_id, "Other User"),
    ]

    event_dal = SimpleNamespace(
        get_by_id=AsyncMock(return_value=SimpleNamespace(created_by=creator_id))
    )
    membership_dal = SimpleNamespace(
        get=AsyncMock(return_value=SimpleNamespace(event_id=event_id, user_id=member_id)),
        get_event_member_count=AsyncMock(return_value=2),
    )
    consent_dal = SimpleNamespace(
        get=AsyncMock(return_value=SimpleNamespace(allow_profile_display=False))
    )
    profile_dal = SimpleNamespace(get_event_directory=AsyncMock(return_value=entries))

    app.dependency_overrides[get_current_user] = lambda: _mock_user(member_id)
    app.dependency_overrides[get_event_dal] = lambda: event_dal
    app.dependency_overrides[get_membership_dal] = lambda: membership_dal
    app.dependency_overrides[get_consent_dal] = lambda: consent_dal
    app.dependency_overrides[get_profile_dal] = lambda: profile_dal

    response = client.get(f"/api/v1/profiles/directory/{event_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["total_count"] == 2
    assert body["hidden_count"] == 1
    assert len(body["entries"]) == 1
    assert body["entries"][0]["user_id"] == str(member_id)


def test_get_event_directory_member_with_missing_consent_sees_only_self(client: TestClient):
    event_id = uuid4()
    creator_id = uuid4()
    member_id = uuid4()
    other_id = uuid4()
    entries = [
        _entry(member_id, "Member User"),
        _entry(other_id, "Other User"),
    ]

    event_dal = SimpleNamespace(
        get_by_id=AsyncMock(return_value=SimpleNamespace(created_by=creator_id))
    )
    membership_dal = SimpleNamespace(
        get=AsyncMock(return_value=SimpleNamespace(event_id=event_id, user_id=member_id)),
        get_event_member_count=AsyncMock(return_value=2),
    )
    consent_dal = SimpleNamespace(get=AsyncMock(return_value=None))
    profile_dal = SimpleNamespace(get_event_directory=AsyncMock(return_value=entries))

    app.dependency_overrides[get_current_user] = lambda: _mock_user(member_id)
    app.dependency_overrides[get_event_dal] = lambda: event_dal
    app.dependency_overrides[get_membership_dal] = lambda: membership_dal
    app.dependency_overrides[get_consent_dal] = lambda: consent_dal
    app.dependency_overrides[get_profile_dal] = lambda: profile_dal

    response = client.get(f"/api/v1/profiles/directory/{event_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["total_count"] == 2
    assert body["hidden_count"] == 1
    assert len(body["entries"]) == 1
    assert body["entries"][0]["user_id"] == str(member_id)


def test_get_event_directory_member_with_consent_off_no_self_entry_returns_empty(
    client: TestClient,
):
    event_id = uuid4()
    creator_id = uuid4()
    member_id = uuid4()
    other_id = uuid4()
    entries = [_entry(other_id, "Other User")]

    event_dal = SimpleNamespace(
        get_by_id=AsyncMock(return_value=SimpleNamespace(created_by=creator_id))
    )
    membership_dal = SimpleNamespace(
        get=AsyncMock(return_value=SimpleNamespace(event_id=event_id, user_id=member_id)),
        get_event_member_count=AsyncMock(return_value=2),
    )
    consent_dal = SimpleNamespace(
        get=AsyncMock(return_value=SimpleNamespace(allow_profile_display=False))
    )
    profile_dal = SimpleNamespace(get_event_directory=AsyncMock(return_value=entries))

    app.dependency_overrides[get_current_user] = lambda: _mock_user(member_id)
    app.dependency_overrides[get_event_dal] = lambda: event_dal
    app.dependency_overrides[get_membership_dal] = lambda: membership_dal
    app.dependency_overrides[get_consent_dal] = lambda: consent_dal
    app.dependency_overrides[get_profile_dal] = lambda: profile_dal

    response = client.get(f"/api/v1/profiles/directory/{event_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["total_count"] == 2
    assert body["hidden_count"] == 2
    assert body["entries"] == []


def test_get_event_directory_hidden_count_is_clamped_non_negative(client: TestClient):
    event_id = uuid4()
    creator_id = uuid4()
    entries = [_entry(uuid4(), "One"), _entry(uuid4(), "Two"), _entry(uuid4(), "Three")]

    event_dal = SimpleNamespace(
        get_by_id=AsyncMock(return_value=SimpleNamespace(created_by=creator_id))
    )
    membership_dal = SimpleNamespace(
        get=AsyncMock(return_value=None),
        get_event_member_count=AsyncMock(return_value=2),
    )
    consent_dal = SimpleNamespace(
        get=AsyncMock(return_value=SimpleNamespace(allow_profile_display=True))
    )
    profile_dal = SimpleNamespace(get_event_directory=AsyncMock(return_value=entries))

    app.dependency_overrides[get_current_user] = lambda: _mock_user(creator_id)
    app.dependency_overrides[get_event_dal] = lambda: event_dal
    app.dependency_overrides[get_membership_dal] = lambda: membership_dal
    app.dependency_overrides[get_consent_dal] = lambda: consent_dal
    app.dependency_overrides[get_profile_dal] = lambda: profile_dal

    response = client.get(f"/api/v1/profiles/directory/{event_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["total_count"] == 2
    assert body["hidden_count"] == 0
    assert len(body["entries"]) == 3
