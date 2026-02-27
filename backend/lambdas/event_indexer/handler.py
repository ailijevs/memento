"""Lambda handler for indexing event attendee faces into Rekognition collections."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.config import get_settings
from app.dals.consent_dal import ConsentDAL
from app.dals.event_dal import EventDAL
from app.dals.profile_dal import ProfileDAL
from app.db.supabase import get_admin_client
from app.schemas.event import EventProcessingStatus, EventUpdate
from app.services.rekognition import RekognitionService

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """AWS Lambda entrypoint."""
    window_minutes = int(event.get("window_minutes", 20)) if isinstance(event, dict) else 20
    return asyncio.run(_run(window_minutes=window_minutes))


async def _run(*, window_minutes: int = 20) -> dict[str, Any]:
    logger.info("Event indexer started window_minutes=%s", window_minutes)
    settings = get_settings()
    if not settings.s3_bucket_name:
        raise RuntimeError("s3_bucket_name must be configured.")

    supabase_client = get_admin_client()
    event_dal = EventDAL(supabase_client)
    consent_dal = ConsentDAL(supabase_client)
    profile_dal = ProfileDAL(supabase_client)

    rekognition_service = RekognitionService()

    events = await event_dal.get_events_pending_indexing(window_minutes=window_minutes)
    logger.info("Found %s event(s) pending indexing", len(events))
    processed_count = 0
    failed_count = 0

    for event_item in events:
        event_id = event_item.event_id
        logger.info("Processing event_id=%s", event_id)
        try:
            await event_dal.update(
                event_id,
                EventUpdate(indexing_status=EventProcessingStatus.IN_PROGRESS),
            )
            logger.info("Set indexing_status=in_progress event_id=%s", event_id)

            collection_id = f"memento_event_{event_id}"
            rekognition_service.ensure_collection_exists(collection_id=collection_id)
            logger.info("Collection ready collection_id=%s", collection_id)

            user_ids = await consent_dal.get_event_recognition_users(event_id)
            logger.info(
                "Found %s user(s) with allow_recognition for event_id=%s", len(user_ids), event_id
            )
            for user_id in user_ids:
                profile = await profile_dal.get_by_user_id(user_id)
                if profile is None or not profile.photo_path:
                    logger.info(
                        "Skipping user_id=%s event_id=%s due to missing profile/photo",
                        user_id,
                        event_id,
                    )
                    continue

                rekognition_service.index_face_from_s3(
                    collection_id=collection_id,
                    bucket_name=settings.s3_bucket_name,
                    object_key=profile.photo_path,
                    image_id=str(user_id),
                )
                logger.info("Indexed face user_id=%s event_id=%s", user_id, event_id)

            await event_dal.update(
                event_id,
                EventUpdate(indexing_status=EventProcessingStatus.COMPLETED),
            )
            logger.info("Set indexing_status=completed event_id=%s", event_id)
            processed_count += 1
        except Exception:
            failed_count += 1
            logger.exception("Failed processing event_id=%s", event_id)
            await event_dal.update(
                event_id,
                EventUpdate(indexing_status=EventProcessingStatus.FAILED),
            )
            logger.info("Set indexing_status=failed event_id=%s", event_id)

    result = {
        "events_scanned": len(events),
        "events_completed": processed_count,
        "events_failed": failed_count,
    }
    logger.info("Event indexer finished result=%s", result)
    return result


if __name__ == "__main__":
    results = asyncio.run(_run())
    print(results)
