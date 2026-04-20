"""Orchestrate full account deletion (owned events, storage, Supabase Auth user)."""

from __future__ import annotations

import logging
from uuid import UUID

from app.schemas.event import EventProcessingStatus
from app.services.rekognition import RekognitionError, RekognitionService
from app.utils.rekognition_helpers import build_event_collection_id
from supabase import Client

logger = logging.getLogger(__name__)

PROFILE_PHOTOS_BUCKET = "profile-photos"


def delete_current_account(*, admin: Client, user_id: UUID) -> None:
    """
    Hard-delete events created by the user (with best-effort Rekognition cleanup),
    remove canonical profile photo from Storage, then delete the Auth user.

    DB rows keyed by user_id (profiles, memberships, consents, etc.) cascade when
    the Auth user is removed. Events created by the user must be removed first
    because ``events.created_by`` references ``auth.users`` with ON DELETE RESTRICT.
    """
    uid_str = str(user_id)

    events_resp = (
        admin.table("events")
        .select("event_id", "indexing_status")
        .eq("created_by", uid_str)
        .execute()
    )

    rekognition = RekognitionService()
    for row in events_resp.data or []:
        eid = row["event_id"]
        idx = (row.get("indexing_status") or "").lower()
        if idx == EventProcessingStatus.COMPLETED.value:
            collection_id = build_event_collection_id(eid)
            try:
                rekognition.delete_collection(collection_id=collection_id)
            except (RekognitionError, RuntimeError, ValueError) as exc:
                logger.warning(
                    "Rekognition collection delete skipped for event_id=%s: %s",
                    eid,
                    exc,
                )
        admin.table("events").delete().eq("event_id", str(eid)).execute()

    try:
        admin.storage.from_(PROFILE_PHOTOS_BUCKET).remove([f"{uid_str}.jpg"])
    except Exception as exc:
        logger.info("Profile photo storage remove skipped or failed: %s", exc)

    admin.auth.admin.delete_user(uid_str, should_soft_delete=False)
