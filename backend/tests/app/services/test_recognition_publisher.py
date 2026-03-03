"""Tests for app.services.recognition_publisher."""

from __future__ import annotations

import importlib
import sys
import time
from pathlib import Path
from typing import Any
from unittest.mock import patch

_ROOT = str(Path(__file__).resolve().parents[3])
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
publisher_module = importlib.import_module("app.services.recognition_publisher")
RecognitionPublisher = publisher_module.RecognitionPublisher


class FakeResponse:
    """Mimics a Supabase query response."""

    def __init__(self, data: list[dict[str, Any]] | None = None) -> None:
        self.data = data or []


class FakeQuery:
    """Mimics a Supabase query builder chain."""

    def __init__(self, rows: list[dict[str, Any]] | None = None) -> None:
        self.inserted: list[dict[str, Any]] = []
        self._rows = rows or []
        self._should_raise = False

    def insert(self, row: dict[str, Any]) -> "FakeQuery":
        if self._should_raise:
            raise RuntimeError("DB insert failed")
        self.inserted.append(row)
        return self

    def delete(self) -> "FakeQuery":
        return self

    def lt(self, column: str, value: str) -> "FakeQuery":
        return self

    def execute(self) -> FakeResponse:
        if self._should_raise:
            raise RuntimeError("DB error")
        return FakeResponse(self._rows)


class FakeSupabaseClient:
    """Mimics a Supabase client for testing."""

    def __init__(self) -> None:
        self.query = FakeQuery()

    def table(self, name: str) -> FakeQuery:
        return self.query


# ---------- publish() tests ----------


def test_publish_inserts_row():
    """publish() inserts a row with correct fields."""
    client = FakeSupabaseClient()
    pub = RecognitionPublisher(client)

    result = pub.publish(
        user_id="wearer-1",
        event_id="event-1",
        matched_user_id="matched-1",
        confidence=0.95,
    )

    assert result is True
    assert len(client.query.inserted) == 1
    row = client.query.inserted[0]
    assert row["user_id"] == "wearer-1"
    assert row["event_id"] == "event-1"
    assert row["matched_user_id"] == "matched-1"
    assert row["confidence"] == 0.95


def test_publish_none_matched_user_id():
    """publish() works with None matched_user_id (no match found)."""
    client = FakeSupabaseClient()
    pub = RecognitionPublisher(client)

    result = pub.publish(
        user_id="wearer-1",
        event_id="event-1",
        matched_user_id=None,
        confidence=0.0,
    )

    assert result is True
    row = client.query.inserted[0]
    assert "matched_user_id" not in row


def test_publish_deduplicates_same_match():
    """publish() suppresses duplicate match within dedup window."""
    client = FakeSupabaseClient()
    pub = RecognitionPublisher(client)

    pub.publish(
        user_id="wearer-1",
        event_id="event-1",
        matched_user_id="matched-1",
        confidence=0.9,
    )
    result = pub.publish(
        user_id="wearer-1",
        event_id="event-1",
        matched_user_id="matched-1",
        confidence=0.91,
    )

    assert result is False
    assert len(client.query.inserted) == 1


def test_publish_allows_different_matches():
    """publish() allows different matched users in same window."""
    client = FakeSupabaseClient()
    pub = RecognitionPublisher(client)

    pub.publish(
        user_id="wearer-1",
        event_id="event-1",
        matched_user_id="matched-1",
        confidence=0.9,
    )
    result = pub.publish(
        user_id="wearer-1",
        event_id="event-1",
        matched_user_id="matched-2",
        confidence=0.85,
    )

    assert result is True
    assert len(client.query.inserted) == 2


def test_publish_allows_same_match_after_window():
    """publish() allows the same match again after dedup window expires."""
    client = FakeSupabaseClient()
    pub = RecognitionPublisher(client)

    pub.publish(
        user_id="wearer-1",
        event_id="event-1",
        matched_user_id="matched-1",
        confidence=0.9,
    )

    with patch.object(
        publisher_module.time,
        "monotonic",
        return_value=time.monotonic() + 3.0,
    ):
        result = pub.publish(
            user_id="wearer-1",
            event_id="event-1",
            matched_user_id="matched-1",
            confidence=0.92,
        )

    assert result is True
    assert len(client.query.inserted) == 2


def test_publish_handles_db_error_gracefully():
    """publish() returns False and does not raise on DB error."""
    client = FakeSupabaseClient()
    client.query._should_raise = True
    pub = RecognitionPublisher(client)

    result = pub.publish(
        user_id="wearer-1",
        event_id="event-1",
        matched_user_id="matched-1",
        confidence=0.9,
    )

    assert result is False


def test_publish_rounds_confidence():
    """publish() rounds confidence to 4 decimal places."""
    client = FakeSupabaseClient()
    pub = RecognitionPublisher(client)

    pub.publish(
        user_id="wearer-1",
        event_id="event-1",
        matched_user_id="matched-1",
        confidence=0.123456789,
    )

    assert client.query.inserted[0]["confidence"] == 0.1235


# ---------- cleanup tests ----------


def test_cleanup_old_results_returns_deleted_count():
    """cleanup_old_results() returns number of deleted rows."""
    fake_rows = [{"id": "1"}, {"id": "2"}, {"id": "3"}]
    client = FakeSupabaseClient()
    client.query = FakeQuery(rows=fake_rows)
    pub = RecognitionPublisher(client)

    deleted = pub.cleanup_old_results(max_age_minutes=5)
    assert deleted == 3


def test_cleanup_old_results_returns_zero_on_no_rows():
    """cleanup_old_results() returns 0 when no rows to delete."""
    client = FakeSupabaseClient()
    pub = RecognitionPublisher(client)

    deleted = pub.cleanup_old_results(max_age_minutes=5)
    assert deleted == 0


def test_cleanup_old_results_handles_error():
    """cleanup_old_results() returns 0 on DB error."""
    client = FakeSupabaseClient()
    client.query._should_raise = True
    pub = RecognitionPublisher(client)

    deleted = pub.cleanup_old_results(max_age_minutes=5)
    assert deleted == 0


# ---------- lazy cleanup tests ----------


def test_lazy_cleanup_triggers_on_first_publish():
    """Lazy cleanup runs on the first publish call."""
    fake_rows = [{"id": "1"}]
    client = FakeSupabaseClient()
    client.query = FakeQuery(rows=fake_rows)
    pub = RecognitionPublisher(client)

    assert pub._last_cleanup == 0.0
    pub.publish(
        user_id="wearer-1",
        event_id="event-1",
        matched_user_id=None,
        confidence=0.0,
    )
    assert pub._last_cleanup > 0.0


def test_lazy_cleanup_skips_when_recent():
    """Lazy cleanup does not run if last cleanup was recent."""
    client = FakeSupabaseClient()
    pub = RecognitionPublisher(client)
    pub._last_cleanup = time.monotonic()

    with patch.object(pub, "cleanup_old_results") as mock_cleanup:
        pub.publish(
            user_id="wearer-1",
            event_id="event-1",
            matched_user_id=None,
            confidence=0.0,
        )
        mock_cleanup.assert_not_called()


# ---------- eviction tests ----------


def test_evict_stale_entries():
    """Stale dedup entries are removed after the window."""
    client = FakeSupabaseClient()
    pub = RecognitionPublisher(client)

    old_time = time.monotonic() - 10.0
    pub._recent[("wearer-1", "matched-1")] = old_time
    pub._recent[("wearer-1", "matched-2")] = time.monotonic()

    pub._evict_stale_entries(time.monotonic())

    assert ("wearer-1", "matched-1") not in pub._recent
    assert ("wearer-1", "matched-2") in pub._recent
