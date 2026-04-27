"""Tests for self-service account deletion (API + service orchestration)."""

from __future__ import annotations

from collections.abc import Generator
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

import app.api.accounts as accounts_api
from app.auth import CurrentUser, get_current_user
from app.db import get_admin_client
from app.main import app
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

    def fake_delete(*, admin, user_id: UUID) -> None:
        called["admin"] = admin
        called["user_id"] = user_id

    monkeypatch.setattr(accounts_api, "delete_current_account", fake_delete)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_admin_client] = lambda: MagicMock(name="admin_client")

    response = client.delete(
        "/api/v1/accounts/me",
        headers={"Authorization": "Bearer fake-access-token"},
    )

    assert response.status_code == 204
    assert response.content == b""
    assert called["user_id"] == user.id
    assert called["admin"] is not None


def test_delete_me_returns_502_when_orchestration_fails(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    """Any exception from delete_current_account is mapped to 502."""

    def boom(*, admin, user_id: UUID) -> None:
        raise RuntimeError("simulated failure")

    monkeypatch.setattr(accounts_api, "delete_current_account", boom)
    app.dependency_overrides[get_current_user] = lambda: _mock_user()
    app.dependency_overrides[get_admin_client] = lambda: MagicMock()

    response = client.delete(
        "/api/v1/accounts/me",
        headers={"Authorization": "Bearer fake-access-token"},
    )

    assert response.status_code == 502
    assert "could not complete" in response.json()["detail"].lower()


class _TableQuery:
    """Minimal PostgREST-style chain for account_deletion tests."""

    def __init__(self, root: "_AdminStub", table: str) -> None:
        self._root = root
        self._table = table
        self._kind: str | None = None
        self._eq_col: str | None = None
        self._eq_val: str | None = None

    def select(self, *_cols: str) -> _TableQuery:
        self._kind = "select"
        return self

    def delete(self) -> _TableQuery:
        self._kind = "delete"
        return self

    def eq(self, col: str, val: str) -> _TableQuery:
        self._eq_col = col
        self._eq_val = val
        return self

    def execute(self) -> SimpleNamespace:
        if self._table == "events" and self._kind == "select" and self._eq_col == "created_by":
            return SimpleNamespace(data=self._root.events_rows)
        if self._table == "events" and self._kind == "delete" and self._eq_col == "event_id":
            event_id = self._eq_val
            assert event_id is not None
            self._root.deleted_event_ids.append(event_id)
            return SimpleNamespace(data=[{"event_id": event_id}])
        raise AssertionError(f"Unexpected table chain: {self._table} {self._kind} {self._eq_col}")


class _StorageBucket:
    def __init__(self, root: "_AdminStub") -> None:
        self._root = root

    def remove(self, keys: list[str]) -> None:
        self._root.removed_storage_keys = list(keys)


class _StorageApi:
    def __init__(self, root: "_AdminStub") -> None:
        self._root = root

    def from_(self, bucket: str) -> _StorageBucket:
        assert bucket == "profile-photos"
        return _StorageBucket(self._root)


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
    """Records operations performed by delete_current_account."""

    def __init__(self, events_rows: object) -> None:
        self.events_rows = events_rows
        self.deleted_event_ids: list[str] = []
        self.removed_storage_keys: list[str] | None = None
        self.deleted_auth_user_id: str | None = None

    def table(self, name: str) -> _TableQuery:
        assert name == "events"
        return _TableQuery(self, name)

    @property
    def storage(self) -> _StorageApi:
        return _StorageApi(self)

    @property
    def auth(self) -> _AuthApi:
        return _AuthApi(self)


def test_delete_current_account_deletes_owned_events_storage_and_auth_user(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Service deletes each owned event row, removes profile photo, then auth user."""
    eid = str(uuid4())
    user_id = uuid4()
    admin = _AdminStub(
        events_rows=[{"event_id": eid, "indexing_status": "pending"}],
    )

    class _StubRekognitionService:
        """Avoid real boto3 in CI; ``delete_current_account`` constructs this."""

        def delete_collection(self, *, collection_id: str) -> dict:
            raise AssertionError("Rekognition should not run when indexing_status is pending")

    monkeypatch.setattr(
        "app.services.account_deletion.RekognitionService",
        _StubRekognitionService,
    )

    delete_current_account(admin=admin, user_id=user_id)

    assert admin.deleted_event_ids == [eid]
    assert admin.removed_storage_keys == [f"{user_id}.jpg"]
    assert admin.deleted_auth_user_id == str(user_id)


def test_delete_current_account_calls_rekognition_when_indexing_completed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Completed-indexing events should attempt Rekognition collection cleanup."""
    eid = str(uuid4())
    user_id = uuid4()
    admin = _AdminStub(
        events_rows=[{"event_id": eid, "indexing_status": "completed"}],
    )

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

    delete_current_account(admin=admin, user_id=user_id)

    assert len(rek_calls) == 1
    assert f"memento_event_{eid}" == rek_calls[0]


def test_delete_current_account_continues_when_rekognition_delete_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Rekognition cleanup is best-effort; event/storage/auth deletion still proceed."""
    eid = str(uuid4())
    user_id = uuid4()
    admin = _AdminStub(
        events_rows=[{"event_id": eid, "indexing_status": "completed"}],
    )

    class _FailingRekognitionService:
        def delete_collection(self, *, collection_id: str) -> dict:
            raise RuntimeError(f"boom for {collection_id}")

    monkeypatch.setattr(
        "app.services.account_deletion.RekognitionService",
        _FailingRekognitionService,
    )

    delete_current_account(admin=admin, user_id=user_id)

    assert admin.deleted_event_ids == [eid]
    assert admin.removed_storage_keys == [f"{user_id}.jpg"]
    assert admin.deleted_auth_user_id == str(user_id)


def test_delete_current_account_skips_malformed_event_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Service ignores malformed rows (non-dict / missing event_id) and still completes."""
    valid_eid = str(uuid4())
    user_id = uuid4()
    admin = _AdminStub(
        events_rows=[
            "not-a-dict",  # ignored
            {"indexing_status": "completed"},  # missing event_id -> ignored
            {"event_id": None, "indexing_status": "completed"},  # ignored
            {"event_id": valid_eid, "indexing_status": "pending"},  # deleted
        ],
    )

    class _StubRekognitionService:
        def delete_collection(self, *, collection_id: str) -> dict:
            raise AssertionError("No completed event with a valid ID should reach Rekognition")

    monkeypatch.setattr(
        "app.services.account_deletion.RekognitionService",
        _StubRekognitionService,
    )

    delete_current_account(admin=admin, user_id=user_id)

    assert admin.deleted_event_ids == [valid_eid]
    assert admin.removed_storage_keys == [f"{user_id}.jpg"]
    assert admin.deleted_auth_user_id == str(user_id)


def test_delete_current_account_handles_non_list_events_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If events query returns non-list data, service treats it as empty safely."""
    user_id = uuid4()
    admin = _AdminStub(events_rows=[])
    admin.events_rows = {"unexpected": "shape"}

    class _StubRekognitionService:
        def delete_collection(self, *, collection_id: str) -> dict:
            raise AssertionError("Rekognition should not run when no valid event rows exist")

    monkeypatch.setattr(
        "app.services.account_deletion.RekognitionService",
        _StubRekognitionService,
    )

    delete_current_account(admin=admin, user_id=user_id)

    assert admin.deleted_event_ids == []
    assert admin.removed_storage_keys == [f"{user_id}.jpg"]
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

    class _FailingStorageBucket(_StorageBucket):
        def __init__(self, root: "_AdminStub") -> None:
            super().__init__(root)

        def remove(self, keys: list[str]) -> None:
            raise RuntimeError(f"storage unavailable for {keys}")

    class _FailingStorageApi(_StorageApi):
        def __init__(self, root: "_AdminStub") -> None:
            super().__init__(root)

        def from_(self, bucket: str) -> _FailingStorageBucket:
            assert bucket == "profile-photos"
            return _FailingStorageBucket(self._root)

    class _AdminWithFailingStorage(_AdminStub):
        @property
        def storage(self) -> _FailingStorageApi:
            return _FailingStorageApi(self)

    failing_admin = _AdminWithFailingStorage(events_rows=[])
    delete_current_account(admin=failing_admin, user_id=user_id)

    assert failing_admin.deleted_event_ids == []
    assert failing_admin.deleted_auth_user_id == str(user_id)
