"""Tests for POST /api/v1/profiles/me/photo-upload-url."""

import os
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

os.environ["DEBUG"] = "false"

from app.api import profiles as profiles_api  # noqa: E402
from app.api.profiles import get_profile_dal  # noqa: E402
from app.auth import CurrentUser, get_current_user  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture
def client():
    """Create a test client and isolate dependency overrides per test."""
    app.dependency_overrides.clear()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _mock_user() -> CurrentUser:
    return CurrentUser(
        id=uuid4(),
        email="test@example.com",
        access_token="test-token",
    )


def test_create_profile_photo_upload_url_success(client: TestClient, monkeypatch):
    """Returns a pre-signed upload URL payload when storage is configured."""
    calls: dict[str, object] = {}

    class FakeS3Service:
        def delete_profile_picture(self, *, s3_key, bucket_name):
            calls["deleted_s3_key"] = s3_key
            calls["delete_bucket_name"] = bucket_name

        def generate_upload_url(
            self,
            *,
            user_id,
            bucket_name,
            source,
            expires_in_seconds,
            content_type,
        ):
            calls.update(
                {
                    "user_id": user_id,
                    "bucket_name": bucket_name,
                    "source": source,
                    "expires_in_seconds": expires_in_seconds,
                    "content_type": content_type,
                }
            )
            return {
                "upload_url": "https://example.com/upload",
                "s3_key": "profiles/test-user-onboarding",
                "content_type": content_type,
            }

    app.dependency_overrides[get_current_user] = _mock_user
    app.dependency_overrides[get_profile_dal] = lambda: SimpleNamespace(
        get_by_user_id=AsyncMock(return_value=None)
    )
    monkeypatch.setattr(
        profiles_api,
        "get_settings",
        lambda: SimpleNamespace(s3_bucket_name="profile-bucket"),
    )
    monkeypatch.setattr(profiles_api, "S3Service", FakeS3Service)

    response = client.post(
        "/api/v1/profiles/me/photo-upload-url",
        json={"content_type": "image/png"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "upload_url": "https://example.com/upload",
        "s3_key": "profiles/test-user-onboarding",
        "content_type": "image/png",
    }
    assert calls["bucket_name"] == "profile-bucket"
    assert calls["source"] == "onboarding"
    assert calls["expires_in_seconds"] == 300
    assert calls["content_type"] == "image/png"
    assert "deleted_s3_key" not in calls


def test_create_profile_photo_upload_url_500_when_bucket_missing(client: TestClient, monkeypatch):
    """Returns 500 when S3 bucket configuration is missing."""
    app.dependency_overrides[get_current_user] = _mock_user
    app.dependency_overrides[get_profile_dal] = lambda: SimpleNamespace(
        get_by_user_id=AsyncMock(return_value=None)
    )
    monkeypatch.setattr(
        profiles_api,
        "get_settings",
        lambda: SimpleNamespace(s3_bucket_name=None),
    )

    response = client.post("/api/v1/profiles/me/photo-upload-url", json={})

    assert response.status_code == 500
    assert response.json()["detail"] == "Profile image storage is not configured."


def test_create_profile_photo_upload_url_400_on_invalid_request(client: TestClient, monkeypatch):
    """Returns 400 when S3Service rejects upload URL input."""

    class RejectingS3Service:
        def generate_upload_url(self, **kwargs):
            raise ValueError("content_type must not be empty.")

    app.dependency_overrides[get_current_user] = _mock_user
    app.dependency_overrides[get_profile_dal] = lambda: SimpleNamespace(
        get_by_user_id=AsyncMock(return_value=None)
    )
    monkeypatch.setattr(
        profiles_api,
        "get_settings",
        lambda: SimpleNamespace(s3_bucket_name="profile-bucket"),
    )
    monkeypatch.setattr(profiles_api, "S3Service", RejectingS3Service)

    response = client.post(
        "/api/v1/profiles/me/photo-upload-url",
        json={"content_type": "   "},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "content_type must not be empty."


def test_create_profile_photo_upload_url_deletes_existing_s3_photo_first(
    client: TestClient, monkeypatch
):
    """Deletes existing S3 photo key before issuing new upload URL."""
    calls: list[str] = []

    class FakeS3Service:
        def delete_profile_picture(self, *, s3_key, bucket_name):
            calls.append(f"delete:{bucket_name}:{s3_key}")

        def generate_upload_url(
            self,
            *,
            user_id,
            bucket_name,
            source,
            expires_in_seconds,
            content_type,
        ):
            calls.append(f"generate:{bucket_name}:{source}:{expires_in_seconds}:{content_type}")
            return {
                "upload_url": "https://example.com/upload",
                "s3_key": "profiles/test-user-onboarding",
                "content_type": content_type,
            }

    app.dependency_overrides[get_current_user] = _mock_user
    app.dependency_overrides[get_profile_dal] = lambda: SimpleNamespace(
        get_by_user_id=AsyncMock(
            return_value=SimpleNamespace(photo_path="profiles/existing-onboarding")
        )
    )
    monkeypatch.setattr(
        profiles_api,
        "get_settings",
        lambda: SimpleNamespace(s3_bucket_name="profile-bucket"),
    )
    monkeypatch.setattr(profiles_api, "S3Service", FakeS3Service)

    response = client.post(
        "/api/v1/profiles/me/photo-upload-url",
        json={"content_type": "image/jpeg"},
    )

    assert response.status_code == 200
    assert calls == [
        "delete:profile-bucket:profiles/existing-onboarding",
        "generate:profile-bucket:onboarding:300:image/jpeg",
    ]


def test_create_profile_photo_upload_url_treats_existing_path_as_raw_key(
    client: TestClient, monkeypatch
):
    """Treats stored photo_path as raw S3 key without transformation."""
    calls: list[str] = []
    existing_photo_path = (
        "https://s3.us-east-2.amazonaws.com/" "profile-bucket/profiles/existing-onboarding"
    )

    class FakeS3Service:
        def delete_profile_picture(self, *, s3_key, bucket_name):
            calls.append(f"delete:{bucket_name}:{s3_key}")

        def generate_upload_url(
            self,
            *,
            user_id,
            bucket_name,
            source,
            expires_in_seconds,
            content_type,
        ):
            calls.append(f"generate:{bucket_name}:{source}:{expires_in_seconds}:{content_type}")
            return {
                "upload_url": "https://example.com/upload",
                "s3_key": "profiles/test-user-onboarding",
                "content_type": content_type,
            }

    app.dependency_overrides[get_current_user] = _mock_user
    app.dependency_overrides[get_profile_dal] = lambda: SimpleNamespace(
        get_by_user_id=AsyncMock(return_value=SimpleNamespace(photo_path=existing_photo_path))
    )
    monkeypatch.setattr(
        profiles_api,
        "get_settings",
        lambda: SimpleNamespace(s3_bucket_name="profile-bucket"),
    )
    monkeypatch.setattr(profiles_api, "S3Service", FakeS3Service)

    response = client.post(
        "/api/v1/profiles/me/photo-upload-url",
        json={"content_type": "image/jpeg"},
    )

    assert response.status_code == 200
    assert calls == [
        f"delete:profile-bucket:{existing_photo_path}",
        "generate:profile-bucket:onboarding:300:image/jpeg",
    ]


def test_create_profile_photo_upload_url_continues_when_delete_missing_key(
    client: TestClient, monkeypatch
):
    """Continues URL generation when existing photo delete reports NoSuchKey."""
    calls: list[str] = []

    class NoSuchKeyError(Exception):
        pass

    class FakeS3Service:
        def delete_profile_picture(self, *, s3_key, bucket_name):
            calls.append(f"delete:{bucket_name}:{s3_key}")
            raise NoSuchKeyError("NoSuchKey")

        def generate_upload_url(
            self,
            *,
            user_id,
            bucket_name,
            source,
            expires_in_seconds,
            content_type,
        ):
            calls.append(f"generate:{bucket_name}:{source}:{expires_in_seconds}:{content_type}")
            return {
                "upload_url": "https://example.com/upload",
                "s3_key": "profiles/test-user-onboarding",
                "content_type": content_type,
            }

    app.dependency_overrides[get_current_user] = _mock_user
    app.dependency_overrides[get_profile_dal] = lambda: SimpleNamespace(
        get_by_user_id=AsyncMock(
            return_value=SimpleNamespace(photo_path="profiles/existing-onboarding")
        )
    )
    monkeypatch.setattr(
        profiles_api,
        "get_settings",
        lambda: SimpleNamespace(s3_bucket_name="profile-bucket"),
    )
    monkeypatch.setattr(profiles_api, "S3Service", FakeS3Service)

    response = client.post(
        "/api/v1/profiles/me/photo-upload-url",
        json={"content_type": "image/jpeg"},
    )

    assert response.status_code == 200
    assert calls == [
        "delete:profile-bucket:profiles/existing-onboarding",
        "generate:profile-bucket:onboarding:300:image/jpeg",
    ]
