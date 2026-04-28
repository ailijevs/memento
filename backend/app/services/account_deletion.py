"""Orchestrate full account deletion (S3 photo, Rekognition, then RPC)."""

from __future__ import annotations

import logging
from collections.abc import Iterable
from uuid import UUID

from app.config import get_settings
from app.dals.event_dal import EventDAL
from app.dals.profile_dal import ProfileDAL
from app.schemas.event import EventProcessingStatus
from app.services.rekognition import RekognitionError, RekognitionService
from app.services.s3 import S3Service
from app.utils.rekognition_helpers import build_event_collection_id
from supabase import Client

logger = logging.getLogger(__name__)


def _iter_completed_event_ids(rows: object, *, kind: str) -> Iterable[str]:
    """Yield ``event_id`` strings from raw rows where ``indexing_status == completed``.

    Skips non-list payloads, non-dict rows, missing/None ``event_id`` values, and
    ``event_id`` values that don't parse as UUIDs. ``kind`` is only used for log
    context (e.g. "owned" / "attended").
    """
    if not isinstance(rows, list):
        return
    for raw in rows:
        if not isinstance(raw, dict):
            continue
        eid_val = raw.get("event_id")
        if eid_val is None:
            continue
        eid = str(eid_val)
        status_raw = raw.get("indexing_status")
        idx = (str(status_raw) if status_raw is not None else "").lower()
        if idx != EventProcessingStatus.COMPLETED.value:
            continue
        try:
            UUID(eid)
        except ValueError:
            logger.warning(
                "Skipping malformed %s event_id during account deletion cleanup: %s",
                kind,
                eid,
            )
            continue
        yield eid


async def delete_current_account(
    *,
    user_id: UUID,
    client: Client,
    profile_dal: ProfileDAL,
    event_dal: EventDAL,
) -> None:
    """Best-effort AWS cleanup, then atomic DB cleanup via the user-scoped RPC.

    Performs the side-effecting cleanup that lives outside Postgres first
    (Rekognition collections for events the user created, Rekognition face
    entries from collections of events they only attended, and the canonical
    profile photo in S3), then invokes the ``delete_my_account`` SECURITY
    DEFINER function using the caller's own JWT. The RPC deletes events the
    user created and the ``auth.users`` row in a single transaction; the
    cascade handles ``profiles``, ``event_memberships``, ``event_consents``,
    and the auth-side session/token tables.

    The caller's authenticated Supabase client (``client``) is required so the
    RPC sees a non-null ``auth.uid()``; no service-role key is used.
    """
    rekognition = RekognitionService()

    owned_rows = await event_dal.get_events_for_account_deletion(user_id)
    for eid in _iter_completed_event_ids(owned_rows, kind="owned"):
        collection_id = build_event_collection_id(eid)
        try:
            rekognition.delete_collection(collection_id=collection_id)
        except (RekognitionError, RuntimeError, ValueError) as exc:
            logger.warning(
                "Rekognition collection delete skipped for event_id=%s: %s",
                eid,
                exc,
            )

    attended_rows = await event_dal.get_attended_events_for_account_deletion(user_id)
    for eid in _iter_completed_event_ids(attended_rows, kind="attended"):
        collection_id = build_event_collection_id(eid)
        try:
            rekognition.delete_faces_by_user(
                collection_id=collection_id,
                user_id=user_id,
            )
        except (RekognitionError, RuntimeError, ValueError) as exc:
            logger.warning(
                "Rekognition face cleanup skipped for attended event_id=%s: %s",
                eid,
                exc,
            )

    photo_path = await profile_dal.get_photo_path(user_id)
    settings = get_settings()
    if photo_path and settings.s3_bucket_name:
        s3_service = S3Service()
        try:
            s3_service.delete_profile_picture(
                s3_key=photo_path,
                bucket_name=settings.s3_bucket_name,
            )
        except Exception as exc:
            logger.info("Profile photo S3 remove skipped or failed: %s", exc)

    client.rpc("delete_my_account", {}).execute()
