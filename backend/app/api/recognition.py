"""API endpoints for facial recognition using AWS Rekognition."""

import time
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import CurrentUser, get_current_user
from app.schemas import (
    CollectionStatsResponse,
    DetectFacesRequest,
    DetectFacesResponse,
    DetectedFace,
    FaceDeleteResponse,
    FaceIndexRequest,
    FaceIndexResponse,
    FaceMatch,
    FrameDetectionRequest,
    FrameDetectionResponse,
    BoundingBox,
)
from app.services.rekognition import (
    RekognitionService,
    RekognitionError,
    FaceNotFoundError,
    CollectionNotFoundError,
    decode_base64_image,
    get_rekognition_service,
)

router = APIRouter(prefix="/recognition", tags=["recognition"])


def _convert_bounding_box(box: dict | None) -> BoundingBox | None:
    """Convert AWS bounding box dict to schema."""
    if not box:
        return None
    return BoundingBox(
        width=box.get("Width", 0),
        height=box.get("Height", 0),
        left=box.get("Left", 0),
        top=box.get("Top", 0),
    )


@router.post("/detect", response_model=FrameDetectionResponse)
async def detect_faces_in_frame(
    request: FrameDetectionRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    rekognition: Annotated[RekognitionService, Depends(get_rekognition_service)],
) -> FrameDetectionResponse:
    """
    Detect and identify faces in a frame from MentraOS smart glasses.

    This endpoint processes a frame capture from the glasses camera,
    detects all faces, and matches them against registered users in
    the Rekognition collection.

    Returns identified users with confidence scores.
    """
    start_time = time.perf_counter()

    try:
        image_bytes = decode_base64_image(request.image_base64)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid base64 image: {str(e)}",
        )

    try:
        await rekognition.ensure_collection_exists()

        detected = await rekognition.detect_faces(image_bytes)
        faces_detected = len(detected)

        matches_raw = await rekognition.search_faces_by_image(
            image_bytes=image_bytes,
            max_faces=request.max_faces,
            threshold=request.threshold,
        )

        matches = [
            FaceMatch(
                user_id=m.get("user_id"),
                face_id=m["face_id"],
                similarity=m["similarity"],
                confidence=m["confidence"],
                bounding_box=_convert_bounding_box(m.get("bounding_box")),
            )
            for m in matches_raw
        ]

        processing_time = (time.perf_counter() - start_time) * 1000

        return FrameDetectionResponse(
            matches=matches,
            faces_detected=faces_detected,
            processing_time_ms=round(processing_time, 2),
            event_id=request.event_id,
        )

    except RekognitionError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Recognition service error: {str(e)}",
        )


@router.post("/index", response_model=FaceIndexResponse, status_code=status.HTTP_201_CREATED)
async def index_user_face(
    request: FaceIndexRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    rekognition: Annotated[RekognitionService, Depends(get_rekognition_service)],
) -> FaceIndexResponse:
    """
    Register the current user's face for recognition.

    The user must provide a clear image of their face. This face will be
    indexed in the Rekognition collection and associated with their user ID.
    """
    try:
        image_bytes = decode_base64_image(request.image_base64)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid base64 image: {str(e)}",
        )

    try:
        await rekognition.ensure_collection_exists()

        result = await rekognition.index_face(
            user_id=current_user.id,
            image_bytes=image_bytes,
        )

        return FaceIndexResponse(
            face_id=result["face_id"],
            user_id=current_user.id,
            confidence=result["confidence"],
            bounding_box=_convert_bounding_box(result.get("bounding_box")),
        )

    except FaceNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No face detected in the image. Please provide a clear photo of your face.",
        )
    except RekognitionError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Recognition service error: {str(e)}",
        )


@router.delete("/faces/me", response_model=FaceDeleteResponse)
async def delete_my_faces(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    rekognition: Annotated[RekognitionService, Depends(get_rekognition_service)],
) -> FaceDeleteResponse:
    """
    Delete all registered faces for the current user.

    Removes all face data associated with the user from the recognition system.
    """
    try:
        deleted_count = await rekognition.delete_faces_by_user(current_user.id)
        return FaceDeleteResponse(
            deleted_count=deleted_count,
            user_id=current_user.id,
        )
    except RekognitionError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Recognition service error: {str(e)}",
        )


@router.post("/detect-only", response_model=DetectFacesResponse)
async def detect_faces_only(
    request: DetectFacesRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    rekognition: Annotated[RekognitionService, Depends(get_rekognition_service)],
) -> DetectFacesResponse:
    """
    Detect faces in an image without identity matching.

    Useful for validating images contain faces before indexing,
    or for face detection without recognition.
    """
    try:
        image_bytes = decode_base64_image(request.image_base64)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid base64 image: {str(e)}",
        )

    try:
        attributes = ["ALL"] if request.include_attributes else ["DEFAULT"]
        faces_raw = await rekognition.detect_faces(image_bytes, attributes=attributes)

        faces = [
            DetectedFace(
                bounding_box=BoundingBox(
                    width=f["bounding_box"].get("Width", 0),
                    height=f["bounding_box"].get("Height", 0),
                    left=f["bounding_box"].get("Left", 0),
                    top=f["bounding_box"].get("Top", 0),
                ),
                confidence=f["confidence"],
                age_range=f.get("age_range"),
                emotions=f.get("emotions"),
                smile=f.get("smile"),
                eyeglasses=f.get("eyeglasses"),
                sunglasses=f.get("sunglasses"),
            )
            for f in faces_raw
        ]

        return DetectFacesResponse(
            faces=faces,
            face_count=len(faces),
        )

    except RekognitionError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Recognition service error: {str(e)}",
        )


@router.get("/stats", response_model=CollectionStatsResponse)
async def get_collection_stats(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    rekognition: Annotated[RekognitionService, Depends(get_rekognition_service)],
) -> CollectionStatsResponse:
    """
    Get statistics about the face recognition collection.

    Returns the number of indexed faces and collection metadata.
    """
    try:
        stats = await rekognition.get_collection_stats()
        return CollectionStatsResponse(
            collection_id=stats["collection_id"],
            face_count=stats["face_count"],
            face_model_version=stats.get("face_model_version"),
            collection_arn=stats.get("collection_arn"),
            creation_timestamp=stats.get("creation_timestamp"),
        )
    except CollectionNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Face collection not found. It will be created when the first face is indexed.",
        )
    except RekognitionError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Recognition service error: {str(e)}",
        )
