"""Lambda handler for deleting event face collections from AWS Rekognition."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.dals.event_dal import EventDAL
from app.db.supabase import get_admin_client
from app.schemas.event import EventProcessingStatus, EventUpdate
from app.services.rekognition import RekognitionService

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """AWS Lambda entrypoint."""
    window_hours = int(event.get("window_hours", 24)) if isinstance(event, dict) else 24
    return asyncio.run(_run(window_hours=window_hours))


async def _run(*, window_hours: int = 24) -> dict[str, Any]:
    logger.info("Event cleanup started window_hours=%s", window_hours)
    supabase_client = get_admin_client()
    event_dal = EventDAL(supabase_client)

    rekognition_service = RekognitionService()

    events = await event_dal.get_events_pending_cleanup(window_hours=window_hours)
    logger.info("Found %s event(s) pending cleanup", len(events))
    processed_count = 0
    failed_count = 0

    for event_item in events:
        event_id = event_item.event_id
        logger.info("Processing cleanup for event_id=%s", event_id)
        try:
            await event_dal.update(
                event_id,
                EventUpdate(cleanup_status=EventProcessingStatus.IN_PROGRESS),
            )
            logger.info("Set cleanup_status=in_progress event_id=%s", event_id)

            collection_id = f"memento_event_{event_id}"
            rekognition_service.delete_collection(collection_id=collection_id)
            logger.info("Deleted collection collection_id=%s", collection_id)

            await event_dal.update(
                event_id,
                EventUpdate(cleanup_status=EventProcessingStatus.COMPLETED),
            )
            logger.info("Set cleanup_status=completed event_id=%s", event_id)
            processed_count += 1
        except Exception:
            failed_count += 1
            logger.exception("Failed cleanup for event_id=%s", event_id)
            await event_dal.update(
                event_id,
                EventUpdate(cleanup_status=EventProcessingStatus.FAILED),
            )
            logger.info("Set cleanup_status=failed event_id=%s", event_id)

    result = {
        "events_scanned": len(events),
        "events_completed": processed_count,
        "events_failed": failed_count,
    }
    logger.info("Event cleanup finished result=%s", result)
    return result
