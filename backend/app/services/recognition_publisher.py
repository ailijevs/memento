"""Service for publishing recognition results to Supabase Realtime."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)

DEDUP_WINDOW_SECONDS = 2.0
DEFAULT_MAX_AGE_MINUTES = 5
LAZY_CLEANUP_INTERVAL_SECONDS = 60.0


class RecognitionPublisher:
    """Publishes face recognition matches to recognition_results table.

    Uses the Supabase admin client (service role) to bypass RLS for inserts.
    The phone app subscribes to this table via Supabase Realtime.
    """

    def __init__(self, admin_client: Any) -> None:
        self.client = admin_client
        self._recent: dict[tuple[str, str], float] = {}
        self._last_cleanup: float = 0.0

    def publish(
        self,
        *,
        user_id: str,
        event_id: str,
        matched_user_id: str | None,
        confidence: float,
    ) -> bool:
        """Publish a recognition result for phone delivery.

        Returns True if the row was inserted, False if deduplicated or failed.
        """
        self._maybe_lazy_cleanup()

        if matched_user_id and self._is_duplicate(user_id, matched_user_id):
            logger.debug(
                "Dedup: skipping %s -> %s (within %.0fs window)",
                user_id,
                matched_user_id,
                DEDUP_WINDOW_SECONDS,
            )
            return False

        try:
            row: dict[str, Any] = {
                "user_id": user_id,
                "event_id": event_id,
                "confidence": round(confidence, 4),
            }
            if matched_user_id:
                row["matched_user_id"] = matched_user_id

            self.client.table("recognition_results").insert(row).execute()

            if matched_user_id:
                self._record_publish(user_id, matched_user_id)

            logger.info(
                "Published recognition: wearer=%s matched=%s confidence=%.2f",
                user_id,
                matched_user_id or "none",
                confidence,
            )
            return True

        except Exception as e:
            logger.error("Failed to publish recognition result: %s", e)
            return False

    def _is_duplicate(self, user_id: str, matched_user_id: str) -> bool:
        """Check if this match was already published within the dedup window."""
        key = (user_id, matched_user_id)
        last_publish = self._recent.get(key)
        if last_publish is None:
            return False
        return (time.monotonic() - last_publish) < DEDUP_WINDOW_SECONDS

    def _record_publish(self, user_id: str, matched_user_id: str) -> None:
        """Record a publish timestamp for deduplication."""
        now = time.monotonic()
        key = (user_id, matched_user_id)
        self._recent[key] = now
        self._evict_stale_entries(now)

    def _evict_stale_entries(self, now: float) -> None:
        """Remove dedup entries older than the window to prevent memory growth."""
        stale_keys = [k for k, t in self._recent.items() if (now - t) >= DEDUP_WINDOW_SECONDS]
        for k in stale_keys:
            del self._recent[k]

    def cleanup_old_results(self, max_age_minutes: int = DEFAULT_MAX_AGE_MINUTES) -> int:
        """Delete recognition results older than max_age_minutes.

        Returns the number of rows deleted.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=max_age_minutes)
        cutoff_iso = cutoff.isoformat()

        try:
            response = (
                self.client.table("recognition_results")
                .delete()
                .lt("created_at", cutoff_iso)
                .execute()
            )
            deleted = len(response.data) if response.data else 0
            if deleted > 0:
                logger.info(
                    "Cleaned up %d recognition results older than %d minutes",
                    deleted,
                    max_age_minutes,
                )
            return deleted

        except Exception as e:
            logger.error("Failed to clean up recognition results: %s", e)
            return 0

    def _maybe_lazy_cleanup(self) -> None:
        """Run cleanup if enough time has passed since the last one."""
        now = time.monotonic()
        if (now - self._last_cleanup) >= LAZY_CLEANUP_INTERVAL_SECONDS:
            self.cleanup_old_results()
            self._last_cleanup = now
