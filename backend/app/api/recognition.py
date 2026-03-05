"""API endpoints for facial recognition using AWS Rekognition."""

import time
from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.dals.event_dal import EventDAL
from app.db.supabase import get_admin_client
from app.schemas import (
    EventProcessingStatus,
    FaceMatch,
    FrameDetectionRequest,
    FrameDetectionResponse,
)
from app.services.rekognition import (
    RekognitionError,
    RekognitionService,
)
from app.utils.rekognition_helpers import build_event_collection_id, decode_base64_image

router = APIRouter(prefix="/recognition", tags=["recognition"])


@router.post("/detect", response_model=FrameDetectionResponse)
async def detect_faces_in_frame(
    request: FrameDetectionRequest,
) -> FrameDetectionResponse:
    """
    Detect and identify faces in a frame from MentraOS smart glasses.

    This endpoint processes a frame capture from the glasses camera,
    detects all faces, and matches them against registered users in
    the Rekognition collection.

    Returns identified users with confidence scores.
    """
    admin_client = get_admin_client()
    event_dal = EventDAL(admin_client)
    # If an event_id is provided, enforce that indexing is completed
    if request.event_id is not None:
        event = await event_dal.get_by_id(UUID(request.event_id))
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
        collection_id = build_event_collection_id(event.event_id)

        matches_raw = rekognition.search_faces_by_image(
            image_bytes=image_bytes,
            collection_id=collection_id,
        )

        matches = [
            FaceMatch(
                user_id=m.get("user_id"),
                face_id=m["face_id"],
                similarity=m["similarity"],
                confidence=m["confidence"],
            )
            for m in matches_raw
        ]

        processing_time = (time.perf_counter() - start_time) * 1000

        return FrameDetectionResponse(
            matches=matches,
            processing_time_ms=round(processing_time, 2),
            event_id=request.event_id,
        )

    except RekognitionError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Recognition service error: {str(e)}",
        )
