"""Tests for self-service account deletion (API + service orchestration)."""

from __future__ import annotations

import asyncio
from collections.abc import Generator
from typing import Any, cast
from unittest.mock import MagicMock
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
    """DELETE /api/v1/profiles/me without Bearer token returns 401."""
    response = client.delete("/api/v1/profiles/me")
    assert response.status_code == 401


def test_delete_me_success(monkeypatch: pytest.MonkeyPatch, client: TestClient) -> None:
    """Happy path: orchestration runs and returns 204."""
    user = _mock_user()
    called: dict[str, object] = {}

    async def fake_delete(
        *,
        user_id: UUID,
        client: object,
        profile_dal: object,
        event_dal: object,
    ) -> None:
        called["user_id"] = user_id
        called["client"] = client
        called["profile_dal"] = profile_dal
        called["event_dal"] = event_dal

    monkeypatch.setattr(accounts_api, "delete_current_account", fake_delete)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[accounts_api.get_profile_dal] = lambda: MagicMock(name="profile_dal")
    app.dependency_overrides[accounts_api.get_event_dal] = lambda: MagicMock(name="event_dal")
    app.dependency_overrides[accounts_api.get_authed_supabase_client] = lambda: MagicMock(
        name="authed_client"
    )

    response = client.delete(
        "/api/v1/profiles/me",
        headers={"Authorization": "Bearer fake-access-token"},
    )

    assert response.status_code == 204
    assert response.content == b""
    assert called["user_id"] == user.id
    assert called["client"] is not None
    assert called["profile_dal"] is not None
    assert called["event_dal"] is not None


def test_delete_me_returns_502_when_orchestration_fails(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    """Any exception from delete_current_account is mapped to 502."""

    async def boom(
        *,
        user_id: UUID,
        client: object,
        profile_dal: object,
        event_dal: object,
    ) -> None:
        raise RuntimeError("simulated failure")

    monkeypatch.setattr(accounts_api, "delete_current_account", boom)
    app.dependency_overrides[get_current_user] = lambda: _mock_user()
    app.dependency_overrides[accounts_api.get_profile_dal] = lambda: MagicMock(name="profile_dal")
    app.dependency_overrides[accounts_api.get_event_dal] = lambda: MagicMock(name="event_dal")
    app.dependency_overrides[accounts_api.get_authed_supabase_client] = lambda: MagicMock(
        name="authed_client"
    )

    response = client.delete(
        "/api/v1/profiles/me",
        headers={"Authorization": "Bearer fake-access-token"},
    )

    assert response.status_code == 502
    assert "could not complete" in response.json()["detail"].lower()


class _RpcCall:
    """Captures ``rpc(name, params).execute()`` invocations on a stub client."""

    def __init__(self, sink: list[tuple[str, dict[str, Any]]], name: str, params: dict[str, Any]):
        self._sink = sink
        self._name = name
        self._params = params

    def execute(self) -> object:
        self._sink.append((self._name, self._params))
        return MagicMock(data=None)


class _ClientStub:
    """Minimal Supabase ``Client``-shaped stub that records RPC invocations."""

    def __init__(self, rpc_should_raise: BaseException | None = None) -> None:
        self.rpc_calls: list[tuple[str, dict[str, Any]]] = []
        self._rpc_should_raise = rpc_should_raise

    def rpc(self, name: str, params: dict[str, Any] | None = None) -> _RpcCall:
        if self._rpc_should_raise is not None:
            raise self._rpc_should_raise
        return _RpcCall(self.rpc_calls, name, params or {})


class _EventDalStub:
    def __init__(
        self,
        events_rows: list[object],
        attended_rows: list[object] | None = None,
    ) -> None:
        self.events_rows = events_rows
        self.attended_rows: list[object] = attended_rows or []

    async def get_events_for_account_deletion(self, user_id: UUID) -> list[object]:
        _ = user_id
        return self.events_rows

    async def get_attended_events_for_account_deletion(self, user_id: UUID) -> list[object]:
        _ = user_id
        return self.attended_rows


class _ProfileDalStub:
    def __init__(self, photo_path: str | None) -> None:
        self.photo_path = photo_path

    async def get_photo_path(self, user_id: UUID) -> str | None:
        _ = user_id
        return self.photo_path


def test_delete_current_account_invokes_delete_my_account_rpc(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Service must call the SECURITY DEFINER ``delete_my_account`` RPC.

    The RPC is the only DB-side cleanup; no service-role / admin client is used.
    """
    user_id = uuid4()
    event_dal = _EventDalStub(events_rows=[])
    profile_dal = _ProfileDalStub(photo_path=None)
    rpc_client = _ClientStub()

    class _StubRekognitionService:
        """Avoid real boto3 in CI; service constructs this."""

        def delete_collection(self, *, collection_id: str) -> dict:
            raise AssertionError("Rekognition should not run when no events exist")

        def delete_faces_by_user(self, *, collection_id: str, user_id: UUID) -> int:
            raise AssertionError("Rekognition should not run when no events exist")

    monkeypatch.setattr(
        "app.services.account_deletion.RekognitionService",
        _StubRekognitionService,
    )
    monkeypatch.setattr(
        account_deletion_service,
        "get_settings",
        lambda: MagicMock(s3_bucket_name=None),
    )

    asyncio.run(
        delete_current_account(
            user_id=user_id,
            client=cast(Any, rpc_client),
            profile_dal=cast(Any, profile_dal),
            event_dal=cast(Any, event_dal),
        )
    )

    assert rpc_client.rpc_calls == [("delete_my_account", {})]


def test_delete_current_account_runs_rekognition_then_s3_then_rpc_for_owned_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Owned-event Rekognition cleanup, S3 photo deletion, and RPC all run in order."""
    eid = str(uuid4())
    user_id = uuid4()
    event_dal = _EventDalStub(events_rows=[{"event_id": eid, "indexing_status": "completed"}])
    profile_dal = _ProfileDalStub(photo_path=f"profiles/{user_id}-onboarding.jpg")
    rpc_client = _ClientStub()

    rek_collection_calls: list[str] = []
    s3_calls: list[str] = []

    class _RecordingRekognitionService:
        def delete_collection(self, *, collection_id: str) -> dict:
            rek_collection_calls.append(collection_id)
            return {"StatusCode": 200}

        def delete_faces_by_user(self, *, collection_id: str, user_id: UUID) -> int:
            raise AssertionError("No attended events in this test")

    class _RecordingS3Service:
        def delete_profile_picture(self, *, s3_key: str, bucket_name: str) -> None:
            s3_calls.append(f"{bucket_name}:{s3_key}")

    monkeypatch.setattr(
        "app.services.account_deletion.RekognitionService",
        _RecordingRekognitionService,
    )
    monkeypatch.setattr(account_deletion_service, "S3Service", _RecordingS3Service)
    monkeypatch.setattr(
        account_deletion_service,
        "get_settings",
        lambda: MagicMock(s3_bucket_name="test-bucket"),
    )

    asyncio.run(
        delete_current_account(
            user_id=user_id,
            client=cast(Any, rpc_client),
            profile_dal=cast(Any, profile_dal),
            event_dal=cast(Any, event_dal),
        )
    )

    assert rek_collection_calls == [f"memento_event_{eid}"]
    assert s3_calls == [f"test-bucket:profiles/{user_id}-onboarding.jpg"]
    assert rpc_client.rpc_calls == [("delete_my_account", {})]


def test_delete_current_account_continues_when_rekognition_collection_delete_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Rekognition collection failure is best-effort; RPC still runs."""
    eid = str(uuid4())
    user_id = uuid4()
    event_dal = _EventDalStub(events_rows=[{"event_id": eid, "indexing_status": "completed"}])
    profile_dal = _ProfileDalStub(photo_path=None)
    rpc_client = _ClientStub()

    class _FailingRekognitionService:
        def delete_collection(self, *, collection_id: str) -> dict:
            raise RuntimeError(f"boom for {collection_id}")

        def delete_faces_by_user(self, *, collection_id: str, user_id: UUID) -> int:
            raise AssertionError("No attended events in this test")

    monkeypatch.setattr(
        "app.services.account_deletion.RekognitionService",
        _FailingRekognitionService,
    )
    monkeypatch.setattr(
        account_deletion_service,
        "get_settings",
        lambda: MagicMock(s3_bucket_name=None),
    )

    asyncio.run(
        delete_current_account(
            user_id=user_id,
            client=cast(Any, rpc_client),
            profile_dal=cast(Any, profile_dal),
            event_dal=cast(Any, event_dal),
        )
    )

    assert rpc_client.rpc_calls == [("delete_my_account", {})]


def test_delete_current_account_skips_malformed_or_pending_event_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Service ignores malformed / pending rows and still completes via RPC."""
    valid_eid = str(uuid4())
    user_id = uuid4()
    event_dal = _EventDalStub(
        events_rows=[
            "not-a-dict",
            {"indexing_status": "completed"},
            {"event_id": None, "indexing_status": "completed"},
            {"event_id": "not-a-uuid", "indexing_status": "completed"},
            {"event_id": valid_eid, "indexing_status": "pending"},
        ],
    )
    profile_dal = _ProfileDalStub(photo_path=None)
    rpc_client = _ClientStub()

    class _StubRekognitionService:
        def delete_collection(self, *, collection_id: str) -> dict:
            raise AssertionError("No completed valid event in this test")

        def delete_faces_by_user(self, *, collection_id: str, user_id: UUID) -> int:
            raise AssertionError("No attended events in this test")

    monkeypatch.setattr(
        "app.services.account_deletion.RekognitionService",
        _StubRekognitionService,
    )
    monkeypatch.setattr(
        account_deletion_service,
        "get_settings",
        lambda: MagicMock(s3_bucket_name=None),
    )

    asyncio.run(
        delete_current_account(
            user_id=user_id,
            client=cast(Any, rpc_client),
            profile_dal=cast(Any, profile_dal),
            event_dal=cast(Any, event_dal),
        )
    )

    assert rpc_client.rpc_calls == [("delete_my_account", {})]


def test_delete_current_account_handles_non_list_events_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If events query returns non-list data, service treats it as empty safely."""
    user_id = uuid4()
    event_dal = _EventDalStub(events_rows=[])
    event_dal.events_rows = cast(Any, {"unexpected": "shape"})
    profile_dal = _ProfileDalStub(photo_path=None)
    rpc_client = _ClientStub()

    class _StubRekognitionService:
        def delete_collection(self, *, collection_id: str) -> dict:
            raise AssertionError("Rekognition should not run on non-list payload")

        def delete_faces_by_user(self, *, collection_id: str, user_id: UUID) -> int:
            raise AssertionError("No attended events in this test")

    monkeypatch.setattr(
        "app.services.account_deletion.RekognitionService",
        _StubRekognitionService,
    )
    monkeypatch.setattr(
        account_deletion_service,
        "get_settings",
        lambda: MagicMock(s3_bucket_name=None),
    )

    asyncio.run(
        delete_current_account(
            user_id=user_id,
            client=cast(Any, rpc_client),
            profile_dal=cast(Any, profile_dal),
            event_dal=cast(Any, event_dal),
        )
    )

    assert rpc_client.rpc_calls == [("delete_my_account", {})]


def test_delete_current_account_continues_when_storage_remove_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """S3 photo delete failure is best-effort and should not block the RPC."""
    user_id = uuid4()
    event_dal = _EventDalStub(events_rows=[])
    profile_dal = _ProfileDalStub(photo_path="profiles/test-onboarding.jpg")
    rpc_client = _ClientStub()

    class _StubRekognitionService:
        def delete_collection(self, *, collection_id: str) -> dict:
            raise AssertionError("No events should trigger Rekognition in this test")

        def delete_faces_by_user(self, *, collection_id: str, user_id: UUID) -> int:
            raise AssertionError("No attended events in this test")

    class _FailingS3Service:
        def delete_profile_picture(self, *, s3_key: str, bucket_name: str) -> None:
            raise RuntimeError(f"storage unavailable for {bucket_name}:{s3_key}")

    monkeypatch.setattr(
        "app.services.account_deletion.RekognitionService",
        _StubRekognitionService,
    )
    monkeypatch.setattr(account_deletion_service, "S3Service", _FailingS3Service)
    monkeypatch.setattr(
        account_deletion_service,
        "get_settings",
        lambda: MagicMock(s3_bucket_name="test-bucket"),
    )

    asyncio.run(
        delete_current_account(
            user_id=user_id,
            client=cast(Any, rpc_client),
            profile_dal=cast(Any, profile_dal),
            event_dal=cast(Any, event_dal),
        )
    )

    assert rpc_client.rpc_calls == [("delete_my_account", {})]


def test_delete_current_account_removes_user_faces_from_attended_event_collections(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """For events the user only attended, the user's faces are removed from the
    event's Rekognition collection (best-effort) without deleting the collection.
    Pending events and malformed rows are skipped, and the RPC still runs.
    """
    user_id = uuid4()
    attended_completed = str(uuid4())
    attended_pending = str(uuid4())
    attended_invalid = "not-a-uuid"
    event_dal = _EventDalStub(
        events_rows=[],
        attended_rows=[
            {"event_id": attended_completed, "indexing_status": "completed"},
            {"event_id": attended_pending, "indexing_status": "pending"},
            {"event_id": attended_invalid, "indexing_status": "completed"},
            "not-a-dict",
            {"indexing_status": "completed"},
        ],
    )
    profile_dal = _ProfileDalStub(photo_path=None)
    rpc_client = _ClientStub()

    delete_faces_calls: list[tuple[str, UUID]] = []

    class _RecordingRekognitionService:
        def delete_collection(self, *, collection_id: str) -> dict:
            raise AssertionError("Owned-event collection delete must not run here")

        def delete_faces_by_user(self, *, collection_id: str, user_id: UUID) -> int:
            delete_faces_calls.append((collection_id, user_id))
            return 1

    monkeypatch.setattr(
        "app.services.account_deletion.RekognitionService",
        _RecordingRekognitionService,
    )
    monkeypatch.setattr(
        account_deletion_service,
        "get_settings",
        lambda: MagicMock(s3_bucket_name=None),
    )

    asyncio.run(
        delete_current_account(
            user_id=user_id,
            client=cast(Any, rpc_client),
            profile_dal=cast(Any, profile_dal),
            event_dal=cast(Any, event_dal),
        )
    )

    assert delete_faces_calls == [(f"memento_event_{attended_completed}", user_id)]
    assert rpc_client.rpc_calls == [("delete_my_account", {})]


def test_delete_current_account_continues_when_attendee_face_cleanup_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Attendee-side face cleanup is best-effort and must not block the RPC."""
    user_id = uuid4()
    attended_eid = str(uuid4())
    event_dal = _EventDalStub(
        events_rows=[],
        attended_rows=[{"event_id": attended_eid, "indexing_status": "completed"}],
    )
    profile_dal = _ProfileDalStub(photo_path=None)
    rpc_client = _ClientStub()

    class _FailingRekognitionService:
        def delete_collection(self, *, collection_id: str) -> dict:
            raise AssertionError("Owned-event collection delete must not run here")

        def delete_faces_by_user(self, *, collection_id: str, user_id: UUID) -> int:
            raise RuntimeError(f"boom for {collection_id} / {user_id}")

    monkeypatch.setattr(
        "app.services.account_deletion.RekognitionService",
        _FailingRekognitionService,
    )
    monkeypatch.setattr(
        account_deletion_service,
        "get_settings",
        lambda: MagicMock(s3_bucket_name=None),
    )

    asyncio.run(
        delete_current_account(
            user_id=user_id,
            client=cast(Any, rpc_client),
            profile_dal=cast(Any, profile_dal),
            event_dal=cast(Any, event_dal),
        )
    )

    assert rpc_client.rpc_calls == [("delete_my_account", {})]


def test_delete_current_account_propagates_rpc_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If the SECURITY DEFINER RPC fails, the service must surface the error
    so the route can map it to a 502. AWS-side cleanup before the RPC must
    still run.
    """
    user_id = uuid4()
    event_dal = _EventDalStub(events_rows=[])
    profile_dal = _ProfileDalStub(photo_path=None)
    rpc_client = _ClientStub(rpc_should_raise=RuntimeError("rpc unavailable"))

    class _StubRekognitionService:
        def delete_collection(self, *, collection_id: str) -> dict:
            raise AssertionError("No events in this test")

        def delete_faces_by_user(self, *, collection_id: str, user_id: UUID) -> int:
            raise AssertionError("No attended events in this test")

    monkeypatch.setattr(
        "app.services.account_deletion.RekognitionService",
        _StubRekognitionService,
    )
    monkeypatch.setattr(
        account_deletion_service,
        "get_settings",
        lambda: MagicMock(s3_bucket_name=None),
    )

    with pytest.raises(RuntimeError, match="rpc unavailable"):
        asyncio.run(
            delete_current_account(
                user_id=user_id,
                client=cast(Any, rpc_client),
                profile_dal=cast(Any, profile_dal),
                event_dal=cast(Any, event_dal),
            )
        )
