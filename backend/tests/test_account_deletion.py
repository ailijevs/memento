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

    def __init__(self, events_rows: list[dict]) -> None:
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

    rek_calls: list[str] = []

    def fake_delete_collection(self, *, collection_id: str) -> dict:
        rek_calls.append(collection_id)
        return {"StatusCode": 200}

    monkeypatch.setattr(
        "app.services.account_deletion.RekognitionService.delete_collection",
        fake_delete_collection,
    )

    delete_current_account(admin=admin, user_id=user_id)  # type: ignore[arg-type]

    assert admin.deleted_event_ids == [eid]
    assert admin.removed_storage_keys == [f"{user_id}.jpg"]
    assert admin.deleted_auth_user_id == str(user_id)
    assert rek_calls == []  # Rekognition only when indexing_status == completed


def test_delete_current_account_calls_rekognition_when_indexing_completed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    eid = str(uuid4())
    user_id = uuid4()
    admin = _AdminStub(
        events_rows=[{"event_id": eid, "indexing_status": "completed"}],
    )

    rek_calls: list[str] = []

    def fake_delete_collection(self, *, collection_id: str) -> dict:
        rek_calls.append(collection_id)
        return {"StatusCode": 200}

    monkeypatch.setattr(
        "app.services.account_deletion.RekognitionService.delete_collection",
        fake_delete_collection,
    )

    delete_current_account(admin=admin, user_id=user_id)  # type: ignore[arg-type]

    assert len(rek_calls) == 1
    assert f"memento_event_{eid}" == rek_calls[0]
