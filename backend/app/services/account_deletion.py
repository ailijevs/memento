"""Orchestrate full account deletion (owned events, S3 photo, Supabase Auth user)."""

from __future__ import annotations

import logging
from uuid import UUID

from app.config import get_settings
from app.dals.event_dal import EventDAL
from app.dals.profile_dal import ProfileDAL
from app.db import get_admin_client
from app.schemas.event import EventProcessingStatus
from app.services.rekognition import RekognitionError, RekognitionService
from app.services.s3 import S3Service
from app.utils.rekognition_helpers import build_event_collection_id

logger = logging.getLogger(__name__)


async def delete_current_account(
    *,
    user_id: UUID,
    profile_dal: ProfileDAL,
    event_dal: EventDAL,
) -> None:
    """
    Hard-delete events created by the user (with best-effort Rekognition cleanup),
    remove canonical profile photo from S3, delete profile row, then delete
    the Supabase Auth user.

    Events created by the user must be removed first
    because ``events.created_by`` references ``auth.users`` with ON DELETE RESTRICT.
    """
    uid_str = str(user_id)
    rekognition = RekognitionService()
    raw_rows = await event_dal.get_events_for_account_deletion(user_id)
    if not isinstance(raw_rows, list):
        raw_rows = []

    for raw in raw_rows:
        if not isinstance(raw, dict):
            continue
        eid_val = raw.get("event_id")
        if eid_val is None:
            continue
        eid = str(eid_val)
        status_raw = raw.get("indexing_status")
        idx = (str(status_raw) if status_raw is not None else "").lower()
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
        try:
            await event_dal.delete(UUID(eid))
        except ValueError:
            logger.warning("Skipping malformed event_id during deletion: %s", eid)

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

    await profile_dal.delete(user_id)

    admin = get_admin_client()
    admin.auth.admin.delete_user(uid_str, should_soft_delete=False)
