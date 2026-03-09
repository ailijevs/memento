"""API endpoints for facial recognition using AWS Rekognition."""

import logging
import time

from fastapi import APIRouter, HTTPException, status

from app.config import get_settings
from app.dals.event_dal import EventDAL
from app.db.supabase import get_admin_client
from app.schemas import (
    EventProcessingStatus,
    FrameDetectionRequest,
    FrameDetectionResponse,
    ProfileCard,
)
from app.services.profile_card_builder import ProfileCardBuilder
from app.services.rekognition import (
    RekognitionError,
    RekognitionService,
)
from app.services.s3 import S3Service
from app.utils.rekognition_helpers import build_event_collection_id, decode_base64_image

router = APIRouter(prefix="/recognition", tags=["recognition"])
logger = logging.getLogger(__name__)


@router.post("/detect", response_model=FrameDetectionResponse)
async def detect_faces_in_frame(
    request: FrameDetectionRequest,
) -> FrameDetectionResponse:
    """
    Detect and identify faces in a frame from MentraOS smart glasses.

    This endpoint processes a frame capture from the glasses camera,
    detects all faces, matches them against registered users via
    Rekognition, and returns profile cards with the matched users'
    name, headline, company, photo, and LinkedIn info.
    """
    admin_client = get_admin_client()
    event_dal = EventDAL(admin_client)

    if request.event_id is not None:
        event = await event_dal.get_by_id(request.event_id)
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found or not accessible.",
            )
        if event.indexing_status == EventProcessingStatus.IN_PROGRESS:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Event indexing is still in progress. Please try again later.",
            )
        if event.indexing_status in {
            EventProcessingStatus.PENDING,
            EventProcessingStatus.FAILED,
        }:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Event indexing has failed or is not yet completed. "
                    "Face recognition is not available for this event."
                ),
            )

    start_time = time.perf_counter()

    try:
        image_bytes = decode_base64_image(request.image_base64)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid base64 image: {str(e)}",
        )

    try:
        rekognition = RekognitionService()
        collection_id = (
            build_event_collection_id(request.event_id)
            if request.event_id is not None
            else "memento_faces"
        )

        matches_raw = rekognition.search_faces_by_image(
            image_bytes=image_bytes,
            collection_id=collection_id,
        )

        card_builder = ProfileCardBuilder(admin_client)
        event_id_str = str(request.event_id) if request.event_id else None
        profile_cards = await card_builder.build_cards(
            matches=matches_raw,
            event_id=event_id_str,
        )
        profile_cards = _attach_presigned_profile_photo_urls(profile_cards)

        processing_time = (time.perf_counter() - start_time) * 1000

        return FrameDetectionResponse(
            matches=profile_cards,
            processing_time_ms=round(processing_time, 2),
            event_id=request.event_id,
        )

    except RekognitionError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Recognition service error: {str(e)}",
        )


def _attach_presigned_profile_photo_urls(profile_cards: list[ProfileCard]) -> list[ProfileCard]:
    """Replace profile card photo_path S3 keys with pre-signed URLs when possible."""
    settings = get_settings()
    if not settings.s3_bucket_name:
        return profile_cards

    s3_service = S3Service()
    cards_with_urls: list[ProfileCard] = []

    for card in profile_cards:
        if not card.photo_path:
            cards_with_urls.append(card)
            continue

        try:
            presigned_url = s3_service.get_profile_picture_presigned_url(
                s3_key=card.photo_path,
                bucket_name=settings.s3_bucket_name,
            )
            cards_with_urls.append(card.model_copy(update={"photo_path": presigned_url}))
        except Exception as exc:
            logger.warning(
                "Failed to pre-sign profile photo for user_id=%s and key=%s: %s",
                card.user_id,
                card.photo_path,
                exc,
            )
            cards_with_urls.append(card)

    return cards_with_urls
