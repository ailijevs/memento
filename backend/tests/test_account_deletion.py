"""Tests for self-service account deletion (API + service orchestration)."""

from __future__ import annotations

import asyncio
from collections.abc import Generator
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

import app.api.profiles as accounts_api
from app.auth import CurrentUser, get_current_user
from app.main import app
from app.services import account_deletion as account_deletion_service
from app.services.account_deletion import delete_current_account


def _mock_user(user_id: UUID | None = None) -> CurrentUser:
    uid = user_id or uuid4()
    return CurrentUser(
        id=uid,
        email="test@example.com",
        access_token="fake-access-token",
    )


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """Yield a TestClient with dependency overrides reset before/after each test."""
    app.dependency_overrides.clear()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_delete_me_requires_auth(client: TestClient) -> None:
    """DELETE /api/v1/accounts/me without Bearer token returns 401."""
    response = client.delete("/api/v1/accounts/me")
    assert response.status_code == 401


def test_delete_me_success(monkeypatch: pytest.MonkeyPatch, client: TestClient) -> None:
    """Happy path: orchestration runs and returns 204."""
    user = _mock_user()
    called: dict[str, object] = {}

    async def fake_delete(*, user_id: UUID, profile_dal, event_dal) -> None:
        called["profile_dal"] = profile_dal
        called["event_dal"] = event_dal
        called["user_id"] = user_id

    monkeypatch.setattr(accounts_api, "delete_current_account", fake_delete)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[accounts_api.get_profile_dal] = lambda: MagicMock(name="profile_dal")
    app.dependency_overrides[accounts_api.get_event_dal] = lambda: MagicMock(name="event_dal")

    response = client.delete(
        "/api/v1/accounts/me",
        headers={"Authorization": "Bearer fake-access-token"},
    )

    assert response.status_code == 204
    assert response.content == b""
    assert called["user_id"] == user.id
    assert called["profile_dal"] is not None
    assert called["event_dal"] is not None


def test_delete_me_returns_502_when_orchestration_fails(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    """Any exception from delete_current_account is mapped to 502."""

    async def boom(*, user_id: UUID, profile_dal, event_dal) -> None:
        raise RuntimeError("simulated failure")

    monkeypatch.setattr(accounts_api, "delete_current_account", boom)
    app.dependency_overrides[get_current_user] = lambda: _mock_user()
    app.dependency_overrides[accounts_api.get_profile_dal] = lambda: MagicMock(name="profile_dal")
    app.dependency_overrides[accounts_api.get_event_dal] = lambda: MagicMock(name="event_dal")

    response = client.delete(
        "/api/v1/accounts/me",
        headers={"Authorization": "Bearer fake-access-token"},
    )

    assert response.status_code == 502
    assert "could not complete" in response.json()["detail"].lower()


class _AuthAdmin:
    def __init__(self, root: "_AdminStub") -> None:
        self._root = root

    def delete_user(self, uid: str, should_soft_delete: bool = False) -> None:
        self._root.deleted_auth_user_id = uid
        assert should_soft_delete is False


class _AuthApi:
    def __init__(self, root: "_AdminStub") -> None:
        self._root = root
        self.admin = _AuthAdmin(root)


class _AdminStub:
    """Records auth-user deletion performed by delete_current_account."""

    def __init__(self) -> None:
        self.deleted_auth_user_id: str | None = None

    @property
    def auth(self) -> _AuthApi:
        return _AuthApi(self)


class _EventDalStub:
    def __init__(self, events_rows: list[object]) -> None:
        self.events_rows = events_rows
        self.deleted_event_ids: list[str] = []

    async def get_events_for_account_deletion(self, user_id: UUID) -> list[object]:
        _ = user_id
        return self.events_rows

    async def delete(self, event_id: UUID) -> bool:
        self.deleted_event_ids.append(str(event_id))
        return True


class _ProfileDalStub:
    def __init__(self, photo_path: str | None) -> None:
        self.photo_path = photo_path
        self.deleted_profile = False

    async def get_photo_path(self, user_id: UUID) -> str | None:
        _ = user_id
        return self.photo_path

    async def delete(self, user_id: UUID) -> bool:
        _ = user_id
        self.deleted_profile = True
        return True


def test_delete_current_account_deletes_owned_events_storage_and_auth_user(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Service deletes owned events, removes S3 photo, then auth user."""
    eid = str(uuid4())
    user_id = uuid4()
    event_dal = _EventDalStub(events_rows=[{"event_id": eid, "indexing_status": "pending"}])
    profile_dal = _ProfileDalStub(photo_path=f"profiles/{user_id}-onboarding.jpg")
    admin = _AdminStub()
    deleted_s3: list[str] = []

    class _StubRekognitionService:
        """Avoid real boto3 in CI; ``delete_current_account`` constructs this."""

        def delete_collection(self, *, collection_id: str) -> dict:
            raise AssertionError("Rekognition should not run when indexing_status is pending")

    class _StubS3Service:
        def delete_profile_picture(self, *, s3_key: str, bucket_name: str) -> None:
            deleted_s3.append(f"{bucket_name}:{s3_key}")

    monkeypatch.setattr(
        "app.services.account_deletion.RekognitionService",
        _StubRekognitionService,
    )
    monkeypatch.setattr(account_deletion_service, "S3Service", _StubS3Service)
    monkeypatch.setattr(
        account_deletion_service,
        "get_settings",
        lambda: MagicMock(s3_bucket_name="test-bucket"),
    )
    monkeypatch.setattr(account_deletion_service, "get_admin_client", lambda: admin)

    asyncio.run(
        delete_current_account(
            user_id=user_id,
            profile_dal=cast(Any, profile_dal),
            event_dal=cast(Any, event_dal),
        )
    )

    assert event_dal.deleted_event_ids == [eid]
    assert deleted_s3 == [f"test-bucket:profiles/{user_id}-onboarding.jpg"]
    assert profile_dal.deleted_profile is True
    assert admin.deleted_auth_user_id == str(user_id)


def test_delete_current_account_calls_rekognition_when_indexing_completed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Completed-indexing events should attempt Rekognition collection cleanup."""
    eid = str(uuid4())
    user_id = uuid4()
    event_dal = _EventDalStub(events_rows=[{"event_id": eid, "indexing_status": "completed"}])
    profile_dal = _ProfileDalStub(photo_path=None)
    admin = _AdminStub()

    rek_calls: list[str] = []

    class _RecordingRekognitionService:
        """Avoid real boto3 in CI while recording ``delete_collection`` calls."""

        def delete_collection(self, *, collection_id: str) -> dict:
            rek_calls.append(collection_id)
            return {"StatusCode": 200}

    monkeypatch.setattr(
        "app.services.account_deletion.RekognitionService",
        _RecordingRekognitionService,
    )

    monkeypatch.setattr(
        account_deletion_service,
        "get_settings",
        lambda: MagicMock(s3_bucket_name=None),
    )
    monkeypatch.setattr(account_deletion_service, "get_admin_client", lambda: admin)

    asyncio.run(
        delete_current_account(
            user_id=user_id,
            profile_dal=cast(Any, profile_dal),
            event_dal=cast(Any, event_dal),
        )
    )

    assert len(rek_calls) == 1
    assert f"memento_event_{eid}" == rek_calls[0]
    assert profile_dal.deleted_profile is True


def test_delete_current_account_continues_when_rekognition_delete_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Rekognition cleanup is best-effort; event/storage/auth deletion still proceed."""
    eid = str(uuid4())
    user_id = uuid4()
    event_dal = _EventDalStub(events_rows=[{"event_id": eid, "indexing_status": "completed"}])
    profile_dal = _ProfileDalStub(photo_path=None)
    admin = _AdminStub()

    class _FailingRekognitionService:
        def delete_collection(self, *, collection_id: str) -> dict:
            raise RuntimeError(f"boom for {collection_id}")

    monkeypatch.setattr(
        "app.services.account_deletion.RekognitionService",
        _FailingRekognitionService,
    )

    monkeypatch.setattr(
        account_deletion_service,
        "get_settings",
        lambda: MagicMock(s3_bucket_name=None),
    )
    monkeypatch.setattr(account_deletion_service, "get_admin_client", lambda: admin)

    asyncio.run(
        delete_current_account(
            user_id=user_id,
            profile_dal=cast(Any, profile_dal),
            event_dal=cast(Any, event_dal),
        )
    )

    assert event_dal.deleted_event_ids == [eid]
    assert profile_dal.deleted_profile is True
    assert admin.deleted_auth_user_id == str(user_id)


def test_delete_current_account_skips_malformed_event_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Service ignores malformed rows (non-dict / missing event_id) and still completes."""
    valid_eid = str(uuid4())
    user_id = uuid4()
    event_dal = _EventDalStub(
        events_rows=[
            "not-a-dict",  # ignored
            {"indexing_status": "completed"},  # missing event_id -> ignored
            {"event_id": None, "indexing_status": "completed"},  # ignored
            {"event_id": valid_eid, "indexing_status": "pending"},  # deleted
        ],
    )
    profile_dal = _ProfileDalStub(photo_path=None)
    admin = _AdminStub()

    class _StubRekognitionService:
        def delete_collection(self, *, collection_id: str) -> dict:
            raise AssertionError("No completed event with a valid ID should reach Rekognition")

    monkeypatch.setattr(
        "app.services.account_deletion.RekognitionService",
        _StubRekognitionService,
    )

    monkeypatch.setattr(
        account_deletion_service,
        "get_settings",
        lambda: MagicMock(s3_bucket_name=None),
    )
    monkeypatch.setattr(account_deletion_service, "get_admin_client", lambda: admin)

    asyncio.run(
        delete_current_account(
            user_id=user_id,
            profile_dal=cast(Any, profile_dal),
            event_dal=cast(Any, event_dal),
        )
    )

    assert event_dal.deleted_event_ids == [valid_eid]
    assert profile_dal.deleted_profile is True
    assert admin.deleted_auth_user_id == str(user_id)


def test_delete_current_account_handles_non_list_events_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If events query returns non-list data, service treats it as empty safely."""
    user_id = uuid4()
    event_dal = _EventDalStub(events_rows=[])
    profile_dal = _ProfileDalStub(photo_path=None)
    admin = _AdminStub()

    class _StubRekognitionService:
        def delete_collection(self, *, collection_id: str) -> dict:
            raise AssertionError("Rekognition should not run when no valid event rows exist")

    monkeypatch.setattr(
        "app.services.account_deletion.RekognitionService",
        _StubRekognitionService,
    )

    monkeypatch.setattr(
        account_deletion_service,
        "get_settings",
        lambda: MagicMock(s3_bucket_name=None),
    )
    monkeypatch.setattr(account_deletion_service, "get_admin_client", lambda: admin)
    monkeypatch.setattr(
        event_dal,
        "get_events_for_account_deletion",
        AsyncMock(return_value={"unexpected": "shape"}),
    )

    asyncio.run(
        delete_current_account(
            user_id=user_id,
            profile_dal=cast(Any, profile_dal),
            event_dal=cast(Any, event_dal),
        )
    )

    assert event_dal.deleted_event_ids == []
    assert profile_dal.deleted_profile is True
    assert admin.deleted_auth_user_id == str(user_id)


def test_delete_current_account_continues_when_storage_remove_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Storage photo delete failure is best-effort and should not block auth deletion."""
    user_id = uuid4()

    class _StubRekognitionService:
        def delete_collection(self, *, collection_id: str) -> dict:
            raise AssertionError("No events should trigger Rekognition in this test")

    monkeypatch.setattr(
        "app.services.account_deletion.RekognitionService",
        _StubRekognitionService,
    )

    event_dal = _EventDalStub(events_rows=[])
    profile_dal = _ProfileDalStub(photo_path="profiles/test-onboarding.jpg")
    admin = _AdminStub()

    class _FailingS3Service:
        def delete_profile_picture(self, *, s3_key: str, bucket_name: str) -> None:
            raise RuntimeError(f"storage unavailable for {bucket_name}:{s3_key}")

    monkeypatch.setattr(account_deletion_service, "S3Service", _FailingS3Service)
    monkeypatch.setattr(
        account_deletion_service,
        "get_settings",
        lambda: MagicMock(s3_bucket_name="test-bucket"),
    )
    monkeypatch.setattr(account_deletion_service, "get_admin_client", lambda: admin)

    asyncio.run(
        delete_current_account(
            user_id=user_id,
            profile_dal=cast(Any, profile_dal),
            event_dal=cast(Any, event_dal),
        )
    )

    assert event_dal.deleted_event_ids == []
    assert profile_dal.deleted_profile is True
    assert admin.deleted_auth_user_id == str(user_id)
