"""Opt-in live integration tests for S3-backed profile photo flows."""

from __future__ import annotations

from datetime import datetime, timezone
from urllib.request import Request, urlopen
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.profiles import get_profile_dal
from app.auth import CurrentUser, get_current_user
from app.config import get_settings
from app.main import app
from app.schemas.profile import ProfileResponse
from app.services.s3 import S3Service


@pytest.fixture
def client():
    app.dependency_overrides.clear()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _mock_user(user_id: UUID) -> CurrentUser:
    return CurrentUser(
        id=user_id,
        email="live-s3-test@example.com",
        access_token="live-s3-test-token",
    )


class _FakeProfileDAL:
    """Minimal DAL stub so the S3 flow can exercise real storage only."""

    def __init__(self, user_id: UUID) -> None:
        self.user_id = user_id
        self.photo_path: str | None = None

    async def get_by_user_id(self, _: UUID) -> ProfileResponse | None:
        if self.photo_path is None:
            return None
        return self._profile_response(self.photo_path)

    async def update(self, _: UUID, data) -> ProfileResponse:
        self.photo_path = data.photo_path
        return self._profile_response(data.photo_path)

    def _profile_response(self, photo_path: str | None) -> ProfileResponse:
        now = datetime.now(timezone.utc)
        return ProfileResponse(
            user_id=self.user_id,
            full_name="Live S3 Test User",
            headline="Integration Test",
            bio=None,
            location=None,
            company=None,
            major=None,
            graduation_year=None,
            linkedin_url=None,
            photo_path=photo_path,
            experiences=[],
            education=[],
            profile_one_liner=None,
            profile_summary=None,
            summary_provider=None,
            summary_updated_at=None,
            created_at=now,
            updated_at=now,
        )


@pytest.mark.live
def test_live_profile_photo_direct_upload_flow_works_with_s3(client: TestClient):
    """Exercise backend-generated S3 upload + confirm flow against a real bucket."""
    settings = get_settings()
    if not settings.s3_bucket_name:
        pytest.skip("S3_BUCKET_NAME is not configured.")
    if not settings.aws_access_key_id or not settings.aws_secret_access_key:
        pytest.skip("AWS credentials are not configured for live S3 testing.")

    user_id = uuid4()
    profile_dal = _FakeProfileDAL(user_id)
    s3_key: str | None = None

    app.dependency_overrides[get_current_user] = lambda: _mock_user(user_id)
    app.dependency_overrides[get_profile_dal] = lambda: profile_dal

    try:
        upload_response = client.post(
            "/api/v1/profiles/me/photo-upload-url",
            json={"content_type": "image/jpeg", "source": "onboarding"},
        )
        assert upload_response.status_code == 200, upload_response.text

        upload_payload = upload_response.json()
        s3_key = upload_payload["s3_key"]

        put_request = Request(
            upload_payload["upload_url"],
            data=b"live-s3-integration-test-image-bytes",
            headers={"Content-Type": upload_payload["content_type"]},
            method="PUT",
        )
        with urlopen(put_request, timeout=30) as put_response:
            assert put_response.status in {200, 204}

        confirm_response = client.post(
            "/api/v1/profiles/me/photo-upload-confirm",
            json={"s3_key": s3_key},
        )
        assert confirm_response.status_code == 200, confirm_response.text
        assert confirm_response.json()["photo_path"] == s3_key

        assert S3Service().profile_picture_exists(
            s3_key=s3_key,
            bucket_name=settings.s3_bucket_name,
        )
    finally:
        if s3_key:
            S3Service().delete_profile_picture(
                s3_key=s3_key,
                bucket_name=settings.s3_bucket_name,
            )
