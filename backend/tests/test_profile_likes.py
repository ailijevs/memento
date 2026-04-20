"""Tests for profile-like endpoints under /api/v1/profiles."""

import os
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from postgrest.exceptions import APIError

os.environ["DEBUG"] = "false"

from app.api.profiles import (  # noqa: E402
    get_event_dal,
    get_membership_dal,
    get_profile_dal,
)
from app.auth import CurrentUser, get_current_user  # noqa: E402
from app.main import app  # noqa: E402
from app.schemas.profile import ProfileLikeResponse  # noqa: E402


@pytest.fixture
def client():
    """Create a test client and isolate dependency overrides per test."""
    app.dependency_overrides.clear()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _mock_user(user_id: UUID) -> CurrentUser:
    return CurrentUser(id=user_id, email="test@example.com", access_token="test-token")


def _like(user_id: UUID, liked_profile_id: UUID, event_id: UUID | None) -> ProfileLikeResponse:
    return ProfileLikeResponse(
        user_id=user_id,
        liked_profile_id=liked_profile_id,
        event_id=event_id,
        event_name="Spring Summit" if event_id else None,
        created_at=datetime.now(timezone.utc),
    )


def test_get_my_profile_likes_returns_rows(client: TestClient):
    user_id = uuid4()
    liked_a = uuid4()
    liked_b = uuid4()
    event_id = uuid4()

    profile_dal = SimpleNamespace(
        get_user_profile_likes=AsyncMock(
            return_value=[
                _like(user_id, liked_a, event_id),
                _like(user_id, liked_b, None),
            ]
        )
    )

    app.dependency_overrides[get_current_user] = lambda: _mock_user(user_id)
    app.dependency_overrides[get_profile_dal] = lambda: profile_dal

    response = client.get("/api/v1/profiles/me/likes")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    assert body[0]["user_id"] == str(user_id)
    assert body[0]["liked_profile_id"] == str(liked_a)
    assert body[0]["event_id"] == str(event_id)
    assert body[0]["event_name"] == "Spring Summit"
    assert body[1]["liked_profile_id"] == str(liked_b)
    assert body[1]["event_id"] is None
    assert body[1]["event_name"] is None
    profile_dal.get_user_profile_likes.assert_awaited_once_with(user_id=user_id)


def test_like_profile_returns_400_for_self_like(client: TestClient):
    user_id = uuid4()
    event_id = uuid4()

    profile_dal = SimpleNamespace(
        get_by_user_id=AsyncMock(),
        create_profile_like=AsyncMock(),
    )
    event_dal = SimpleNamespace(get_by_id=AsyncMock())
    membership_dal = SimpleNamespace(get=AsyncMock())

    app.dependency_overrides[get_current_user] = lambda: _mock_user(user_id)
    app.dependency_overrides[get_profile_dal] = lambda: profile_dal
    app.dependency_overrides[get_event_dal] = lambda: event_dal
    app.dependency_overrides[get_membership_dal] = lambda: membership_dal

    response = client.post(f"/api/v1/profiles/{user_id}/like", json={"event_id": str(event_id)})

    assert response.status_code == 400
    assert response.json()["detail"] == "You cannot like your own profile."
    event_dal.get_by_id.assert_not_awaited()
    membership_dal.get.assert_not_awaited()
    profile_dal.get_by_user_id.assert_not_awaited()
    profile_dal.create_profile_like.assert_not_awaited()


def test_like_profile_returns_404_when_event_not_found(client: TestClient):
    user_id = uuid4()
    target_user_id = uuid4()
    event_id = uuid4()

    profile_dal = SimpleNamespace(
        get_by_user_id=AsyncMock(),
        create_profile_like=AsyncMock(),
    )
    event_dal = SimpleNamespace(get_by_id=AsyncMock(return_value=None))
    membership_dal = SimpleNamespace(get=AsyncMock())

    app.dependency_overrides[get_current_user] = lambda: _mock_user(user_id)
    app.dependency_overrides[get_profile_dal] = lambda: profile_dal
    app.dependency_overrides[get_event_dal] = lambda: event_dal
    app.dependency_overrides[get_membership_dal] = lambda: membership_dal

    response = client.post(
        f"/api/v1/profiles/{target_user_id}/like", json={"event_id": str(event_id)}
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Event not found."
    membership_dal.get.assert_not_awaited()
    profile_dal.get_by_user_id.assert_not_awaited()
    profile_dal.create_profile_like.assert_not_awaited()


def test_like_profile_returns_403_when_user_not_event_member(client: TestClient):
    user_id = uuid4()
    target_user_id = uuid4()
    event_id = uuid4()

    profile_dal = SimpleNamespace(
        get_by_user_id=AsyncMock(),
        create_profile_like=AsyncMock(),
    )
    event_dal = SimpleNamespace(
        get_by_id=AsyncMock(return_value=SimpleNamespace(event_id=event_id))
    )
    membership_dal = SimpleNamespace(get=AsyncMock(return_value=None))

    app.dependency_overrides[get_current_user] = lambda: _mock_user(user_id)
    app.dependency_overrides[get_profile_dal] = lambda: profile_dal
    app.dependency_overrides[get_event_dal] = lambda: event_dal
    app.dependency_overrides[get_membership_dal] = lambda: membership_dal

    response = client.post(
        f"/api/v1/profiles/{target_user_id}/like", json={"event_id": str(event_id)}
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "You are not a member of this event."
    membership_dal.get.assert_awaited_once_with(event_id=event_id, user_id=user_id)
    profile_dal.get_by_user_id.assert_not_awaited()
    profile_dal.create_profile_like.assert_not_awaited()


def test_like_profile_returns_404_when_target_profile_not_visible(client: TestClient):
    user_id = uuid4()
    target_user_id = uuid4()
    event_id = uuid4()

    profile_dal = SimpleNamespace(
        get_by_user_id=AsyncMock(return_value=None),
        create_profile_like=AsyncMock(),
    )
    event_dal = SimpleNamespace(
        get_by_id=AsyncMock(return_value=SimpleNamespace(event_id=event_id))
    )
    membership_dal = SimpleNamespace(
        get=AsyncMock(return_value=SimpleNamespace(event_id=event_id, user_id=user_id))
    )

    app.dependency_overrides[get_current_user] = lambda: _mock_user(user_id)
    app.dependency_overrides[get_profile_dal] = lambda: profile_dal
    app.dependency_overrides[get_event_dal] = lambda: event_dal
    app.dependency_overrides[get_membership_dal] = lambda: membership_dal

    response = client.post(
        f"/api/v1/profiles/{target_user_id}/like", json={"event_id": str(event_id)}
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Profile not found or not visible."
    profile_dal.get_by_user_id.assert_awaited_once_with(target_user_id)
    profile_dal.create_profile_like.assert_not_awaited()


def test_like_profile_returns_201_on_success(client: TestClient):
    user_id = uuid4()
    target_user_id = uuid4()
    event_id = uuid4()
    created_like = _like(user_id, target_user_id, event_id)

    profile_dal = SimpleNamespace(
        get_by_user_id=AsyncMock(return_value=SimpleNamespace(user_id=target_user_id)),
        create_profile_like=AsyncMock(return_value=created_like),
    )
    event_dal = SimpleNamespace(
        get_by_id=AsyncMock(return_value=SimpleNamespace(event_id=event_id))
    )
    membership_dal = SimpleNamespace(
        get=AsyncMock(return_value=SimpleNamespace(event_id=event_id, user_id=user_id))
    )

    app.dependency_overrides[get_current_user] = lambda: _mock_user(user_id)
    app.dependency_overrides[get_profile_dal] = lambda: profile_dal
    app.dependency_overrides[get_event_dal] = lambda: event_dal
    app.dependency_overrides[get_membership_dal] = lambda: membership_dal

    response = client.post(
        f"/api/v1/profiles/{target_user_id}/like", json={"event_id": str(event_id)}
    )

    assert response.status_code == 201
    body = response.json()
    assert body["user_id"] == str(user_id)
    assert body["liked_profile_id"] == str(target_user_id)
    assert body["event_id"] == str(event_id)
    profile_dal.create_profile_like.assert_awaited_once_with(
        user_id=user_id,
        liked_profile_id=target_user_id,
        event_id=event_id,
    )


def test_like_profile_returns_409_on_duplicate(client: TestClient):
    user_id = uuid4()
    target_user_id = uuid4()
    event_id = uuid4()

    duplicate_error = APIError(
        {
            "code": "23505",
            "message": "duplicate key value violates unique constraint",
            "details": "",
            "hint": "",
        }
    )

    profile_dal = SimpleNamespace(
        get_by_user_id=AsyncMock(return_value=SimpleNamespace(user_id=target_user_id)),
        create_profile_like=AsyncMock(side_effect=duplicate_error),
    )
    event_dal = SimpleNamespace(
        get_by_id=AsyncMock(return_value=SimpleNamespace(event_id=event_id))
    )
    membership_dal = SimpleNamespace(
        get=AsyncMock(return_value=SimpleNamespace(event_id=event_id, user_id=user_id))
    )

    app.dependency_overrides[get_current_user] = lambda: _mock_user(user_id)
    app.dependency_overrides[get_profile_dal] = lambda: profile_dal
    app.dependency_overrides[get_event_dal] = lambda: event_dal
    app.dependency_overrides[get_membership_dal] = lambda: membership_dal

    response = client.post(
        f"/api/v1/profiles/{target_user_id}/like", json={"event_id": str(event_id)}
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Profile already liked for this event."


def test_unlike_profile_returns_204_on_success(client: TestClient):
    user_id = uuid4()
    target_user_id = uuid4()
    profile_dal = SimpleNamespace(
        delete_profile_like=AsyncMock(return_value=True),
    )

    app.dependency_overrides[get_current_user] = lambda: _mock_user(user_id)
    app.dependency_overrides[get_profile_dal] = lambda: profile_dal

    response = client.delete(f"/api/v1/profiles/{target_user_id}/like")

    assert response.status_code == 204
    profile_dal.delete_profile_like.assert_awaited_once_with(
        user_id=user_id,
        liked_profile_id=target_user_id,
    )


def test_unlike_profile_returns_404_when_not_found(client: TestClient):
    user_id = uuid4()
    target_user_id = uuid4()
    profile_dal = SimpleNamespace(
        delete_profile_like=AsyncMock(return_value=False),
    )

    app.dependency_overrides[get_current_user] = lambda: _mock_user(user_id)
    app.dependency_overrides[get_profile_dal] = lambda: profile_dal

    response = client.delete(f"/api/v1/profiles/{target_user_id}/like")

    assert response.status_code == 404
    assert response.json()["detail"] == "Like not found."
    profile_dal.delete_profile_like.assert_awaited_once_with(
        user_id=user_id,
        liked_profile_id=target_user_id,
    )
