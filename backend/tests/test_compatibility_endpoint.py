"""Integration tests for GET /api/v1/profiles/{user_id}/compatibility.

Exercises the full request path from HTTP through the FastAPI route handler
into CompatibilityService, mocking only ProfileDAL so no real DB is needed.
"""

import os
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

os.environ["DEBUG"] = "false"

from fastapi.testclient import TestClient  # noqa: E402

from app.api.profiles import get_admin_profile_dal  # noqa: E402
from app.auth import CurrentUser, get_current_user  # noqa: E402
from app.main import app  # noqa: E402
from app.schemas import ProfileResponse  # noqa: E402

_NOW = datetime.now(timezone.utc)


def _profile(**kwargs) -> ProfileResponse:
    defaults = dict(
        user_id=uuid4(),
        full_name="Test User",
        headline=None,
        bio=None,
        location=None,
        company=None,
        major=None,
        graduation_year=None,
        linkedin_url=None,
        photo_path=None,
        experiences=None,
        education=None,
        profile_one_liner=None,
        profile_summary=None,
        summary_provider=None,
        summary_updated_at=None,
        created_at=_NOW,
        updated_at=_NOW,
    )
    defaults.update(kwargs)
    return ProfileResponse(**defaults)  # type: ignore[arg-type]


def _mock_user(user_id):
    return CurrentUser(id=user_id, email="sasha@test.com", access_token="fake-token")


def _override_dals(dal):
    """Override the admin DAL used for both viewer and target profile fetches."""
    app.dependency_overrides[get_admin_profile_dal] = lambda: dal


def test_compatibility_endpoint_self_returns_400():
    """Cannot compute compatibility between a user and themselves."""
    user_id = uuid4()
    dal = SimpleNamespace(get_by_user_id=AsyncMock())

    app.dependency_overrides[get_current_user] = lambda: _mock_user(user_id)
    _override_dals(dal)

    try:
        with TestClient(app) as client:
            response = client.get(f"/api/v1/profiles/{user_id}/compatibility")
        assert response.status_code == 400
        assert "yourself" in response.json()["detail"].lower()
        dal.get_by_user_id.assert_not_awaited()
    finally:
        app.dependency_overrides.clear()


def test_compatibility_endpoint_missing_viewer_profile_still_returns_result():
    """No-profile viewer (device/kiosk account) gets a 200 with the target's starters."""
    viewer_id = uuid4()
    target_id = uuid4()
    target_profile = _profile(user_id=target_id, full_name="Bob", headline="ML Engineer")

    async def fake_get(uid):
        return None if uid == viewer_id else target_profile

    dal = SimpleNamespace(get_by_user_id=fake_get)

    app.dependency_overrides[get_current_user] = lambda: _mock_user(viewer_id)
    _override_dals(dal)

    try:
        with TestClient(app) as client:
            response = client.get(f"/api/v1/profiles/{target_id}/compatibility")
        assert response.status_code == 200
        body = response.json()
        assert isinstance(body["score"], (int, float))
        assert len(body["conversation_starters"]) >= 1
    finally:
        app.dependency_overrides.clear()


def test_compatibility_endpoint_missing_target_profile_returns_404():
    """Returns 404 when the target user profile is not found or not visible (RLS)."""
    viewer_id = uuid4()
    target_id = uuid4()
    viewer_profile = _profile(user_id=viewer_id, full_name="Sasha")

    call_count = 0

    async def fake_get(uid):
        nonlocal call_count
        call_count += 1
        return viewer_profile if uid == viewer_id else None

    dal = SimpleNamespace(get_by_user_id=fake_get)

    app.dependency_overrides[get_current_user] = lambda: _mock_user(viewer_id)
    _override_dals(dal)

    try:
        with TestClient(app) as client:
            response = client.get(f"/api/v1/profiles/{target_id}/compatibility")
        assert response.status_code == 404
        assert "target profile" in response.json()["detail"].lower()
    finally:
        app.dependency_overrides.clear()


@patch("app.services.compatibility.get_settings")
def test_compatibility_endpoint_returns_score_and_fields(mock_settings):
    """Shared company produces a non-zero rule-based score with conversation starters."""
    mock_settings.return_value = MagicMock(openai_api_key=None)
    viewer_id = uuid4()
    target_id = uuid4()
    viewer_profile = _profile(user_id=viewer_id, full_name="Sasha", company="Memento")
    target_profile = _profile(user_id=target_id, full_name="Alice", company="Memento")

    async def fake_get(uid):
        if uid == viewer_id:
            return viewer_profile
        return target_profile

    dal = SimpleNamespace(get_by_user_id=fake_get)

    app.dependency_overrides[get_current_user] = lambda: _mock_user(viewer_id)
    _override_dals(dal)

    try:
        with TestClient(app) as client:
            response = client.get(f"/api/v1/profiles/{target_id}/compatibility")
        assert response.status_code == 200
        body = response.json()
        assert body["score"] == 30.0
        assert "Memento" in body["shared_companies"]
        assert body["shared_schools"] == []
        assert len(body["conversation_starters"]) >= 1
        assert "Memento" in body["conversation_starters"][0]
    finally:
        app.dependency_overrides.clear()


@patch("app.services.compatibility.get_settings")
def test_compatibility_endpoint_no_overlap_returns_zero_score(mock_settings):
    """Users with no shared background yield a rule-based score of 0."""
    mock_settings.return_value = MagicMock(openai_api_key=None)
    viewer_id = uuid4()
    target_id = uuid4()
    viewer_profile = _profile(user_id=viewer_id, full_name="Sasha", company="Memento")
    target_profile = _profile(user_id=target_id, full_name="Bob", company="Other Corp")

    async def fake_get(uid):
        return viewer_profile if uid == viewer_id else target_profile

    dal = SimpleNamespace(get_by_user_id=fake_get)

    app.dependency_overrides[get_current_user] = lambda: _mock_user(viewer_id)
    _override_dals(dal)

    try:
        with TestClient(app) as client:
            response = client.get(f"/api/v1/profiles/{target_id}/compatibility")
        assert response.status_code == 200
        body = response.json()
        assert body["score"] == 0.0
        assert body["shared_companies"] == []
        assert body["shared_schools"] == []
        assert body["shared_fields"] == []
    finally:
        app.dependency_overrides.clear()


@patch("app.services.compatibility.get_settings")
def test_compatibility_endpoint_shared_school_adds_twenty_five_points(mock_settings):
    """Shared school correctly contributes 25 rule-based points to the score."""
    mock_settings.return_value = MagicMock(openai_api_key=None)
    viewer_id = uuid4()
    target_id = uuid4()
    viewer_profile = _profile(
        user_id=viewer_id,
        full_name="Sasha",
        education=[{"school": "Purdue University", "degree": "BS"}],
    )
    target_profile = _profile(
        user_id=target_id,
        full_name="Alice",
        education=[{"school": "Purdue University", "degree": "MS"}],
    )

    async def fake_get(uid):
        return viewer_profile if uid == viewer_id else target_profile

    dal = SimpleNamespace(get_by_user_id=fake_get)

    app.dependency_overrides[get_current_user] = lambda: _mock_user(viewer_id)
    _override_dals(dal)

    try:
        with TestClient(app) as client:
            response = client.get(f"/api/v1/profiles/{target_id}/compatibility")
        assert response.status_code == 200
        body = response.json()
        assert body["score"] == 25.0
        assert len(body["shared_schools"]) == 1
    finally:
        app.dependency_overrides.clear()
