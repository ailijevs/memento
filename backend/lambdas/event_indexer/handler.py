"""Lambda handler for indexing event attendee faces into Rekognition collections."""

from __future__ import annotations

import asyncio
from typing import Any

from app.config import get_settings
from app.dals.consent_dal import ConsentDAL
from app.dals.event_dal import EventDAL
from app.dals.profile_dal import ProfileDAL
from app.db.supabase import get_admin_client
from app.schemas.event import EventProcessingStatus, EventUpdate
from app.services.rekognition import RekognitionService


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """AWS Lambda entrypoint."""
    window_minutes = int(event.get("window_minutes", 20)) if isinstance(event, dict) else 20
    return asyncio.run(_run(window_minutes=window_minutes))


async def _run(*, window_minutes: int) -> dict[str, Any]:
    settings = get_settings()
    if not settings.s3_bucket_name:
        raise RuntimeError("s3_bucket_name must be configured.")

    supabase_client = get_admin_client()
    event_dal = EventDAL(supabase_client)
    consent_dal = ConsentDAL(supabase_client)
    profile_dal = ProfileDAL(supabase_client)

    rekognition_service = RekognitionService()

    events = await event_dal.get_events_pending_indexing(window_minutes=window_minutes)
    processed_count = 0
    failed_count = 0

    for event_item in events:
        event_id = event_item.event_id
        try:
            await event_dal.update(
                event_id,
                EventUpdate(indexing_status=EventProcessingStatus.IN_PROGRESS),
            )

            collection_id = f"memento_event_{event_id}"
            rekognition_service.ensure_collection_exists(collection_id=collection_id)

            user_ids = await consent_dal.get_event_recognition_users(event_id)
            for user_id in user_ids:
                profile = await profile_dal.get_by_user_id(user_id)
                if profile is None or not profile.photo_path:
                    continue

                rekognition_service.index_face_from_s3(
                    collection_id=collection_id,
                    bucket_name=settings.s3_bucket_name,
                    object_key=profile.photo_path,
                    image_id=str(user_id),
                )

            await event_dal.update(
                event_id,
                EventUpdate(indexing_status=EventProcessingStatus.COMPLETED),
            )
            processed_count += 1
        except Exception:
            failed_count += 1
            await event_dal.update(
                event_id,
                EventUpdate(indexing_status=EventProcessingStatus.FAILED),
            )

    return {
        "events_scanned": len(events),
        "events_completed": processed_count,
        "events_failed": failed_count,
    }
