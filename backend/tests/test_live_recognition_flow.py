"""Opt-in live integration tests for the recognition route."""

from __future__ import annotations

import base64
import os
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.auth.dependencies import CurrentUser, get_current_user
from app.config import get_settings
from app.main import app


def _env(name: str) -> str | None:
    raw = os.environ.get(name)
    if raw is None:
        return None
    stripped = raw.strip()
    return stripped or None


@pytest.fixture
def client():
    app.dependency_overrides.clear()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _mock_user() -> CurrentUser:
    return CurrentUser(
        id=uuid4(),
        email="live-recognition-test@example.com",
        access_token="live-recognition-test-token",
    )


@pytest.mark.live
def test_live_recognition_detect_returns_seeded_profile_match(client: TestClient):
    """Exercise the real recognition route with a seeded face image and profile."""
    image_path_raw = _env("MEMENTO_LIVE_RECOGNITION_IMAGE_PATH")
    expected_user_id = _env("MEMENTO_LIVE_RECOGNITION_EXPECTED_USER_ID")
    missing_env: list[str] = []
    if not image_path_raw:
        missing_env.append("MEMENTO_LIVE_RECOGNITION_IMAGE_PATH")
    if not expected_user_id:
        missing_env.append("MEMENTO_LIVE_RECOGNITION_EXPECTED_USER_ID")
    if missing_env:
        pytest.skip(
            "Missing required env var(s) for live recognition test: " + ", ".join(missing_env)
        )

    assert image_path_raw is not None
    assert expected_user_id is not None

    image_path = Path(image_path_raw)
    if not image_path.exists():
        pytest.skip(
            "Recognition image file does not exist for "
            f"MEMENTO_LIVE_RECOGNITION_IMAGE_PATH: {image_path}"
        )

    settings = get_settings()
    headers = {"Content-Type": "application/json"}
    if settings.hash_to_client:
        api_key = _env("MEMENTO_LIVE_RECOGNITION_API_KEY")
        if not api_key:
            pytest.skip(
                "Recognition API key hashes are configured, but "
                "MEMENTO_LIVE_RECOGNITION_API_KEY is missing."
            )
        headers["X-Recognition-Api-Key"] = api_key

    app.dependency_overrides[get_current_user] = _mock_user

    image_base64 = base64.b64encode(image_path.read_bytes()).decode("ascii")
    response = client.post(
        "/api/v1/recognition/detect",
        json={"image_base64": image_base64, "event_id": None},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    matches = payload["matches"]
    assert matches, "Expected at least one live recognition match."

    matched_user_ids = {match["user_id"] for match in matches}
    assert expected_user_id in matched_user_ids

    matched_profile = next(match for match in matches if match["user_id"] == expected_user_id)
    assert matched_profile["full_name"]
    assert matched_profile["face_similarity"] > 0
