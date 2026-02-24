"""Pydantic schemas for facial recognition operations."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class BoundingBox(BaseModel):
    """Bounding box coordinates for a detected face."""

    width: float = Field(..., ge=0, le=1, description="Width as fraction of image")
    height: float = Field(..., ge=0, le=1, description="Height as fraction of image")
    left: float = Field(..., ge=0, le=1, description="Left position as fraction")
    top: float = Field(..., ge=0, le=1, description="Top position as fraction")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class FaceMatch(BaseModel):
    """A matched face from the recognition collection."""

    user_id: str | None = Field(None, description="User UUID if face is registered")
    face_id: str = Field(..., description="Rekognition face ID")
    similarity: float = Field(..., ge=0, le=100, description="Match confidence %")
    confidence: float = Field(..., ge=0, le=100, description="Detection confidence %")
    bounding_box: BoundingBox | None = None


class DetectedFace(BaseModel):
    """A detected face in an image (without identity matching)."""

    bounding_box: BoundingBox
    confidence: float = Field(..., ge=0, le=100)
    age_range: dict[str, int] | None = None
    emotions: list[dict[str, Any]] | None = None
    smile: dict[str, Any] | None = None
    eyeglasses: dict[str, Any] | None = None
    sunglasses: dict[str, Any] | None = None


class FrameDetectionRequest(BaseModel):
    """Request to detect and identify faces in a frame from MentraOS glasses."""

    image_base64: str = Field(
        ...,
        description="Base64 encoded image from glasses camera",
        min_length=100,
    )
    event_id: UUID | None = Field(
        None,
        description="Optional event context to filter matches",
    )
    max_faces: int | None = Field(
        None,
        ge=1,
        le=20,
        description="Maximum number of faces to return",
    )
    threshold: float | None = Field(
        None,
        ge=0,
        le=100,
        description="Minimum confidence threshold for matches",
    )


class FrameDetectionResponse(BaseModel):
    """Response containing identified faces from a frame."""

    matches: list[FaceMatch] = Field(
        default_factory=list,
        description="List of identified faces",
    )
    faces_detected: int = Field(..., description="Total faces detected in frame")
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")
    event_id: UUID | None = None


class FaceIndexRequest(BaseModel):
    """Request to register a user's face in the recognition system."""

    image_base64: str = Field(
        ...,
        description="Base64 encoded image containing the user's face",
        min_length=100,
    )


class FaceIndexResponse(BaseModel):
    """Response after successfully indexing a face."""

    face_id: str = Field(..., description="Rekognition face ID")
    user_id: UUID = Field(..., description="Associated user UUID")
    confidence: float = Field(..., description="Face detection confidence")
    bounding_box: BoundingBox | None = None
    indexed_at: datetime = Field(default_factory=datetime.utcnow)


class FaceDeleteResponse(BaseModel):
    """Response after deleting faces."""

    deleted_count: int = Field(..., description="Number of faces deleted")
    user_id: UUID


class CollectionStatsResponse(BaseModel):
    """Statistics about the face recognition collection."""

    collection_id: str
    face_count: int
    face_model_version: str | None = None
    collection_arn: str | None = None
    creation_timestamp: datetime | None = None


class DetectFacesRequest(BaseModel):
    """Request to detect faces without identity matching."""

    image_base64: str = Field(
        ...,
        description="Base64 encoded image",
        min_length=100,
    )
    include_attributes: bool = Field(
        False,
        description="Include detailed face attributes",
    )


class DetectFacesResponse(BaseModel):
    """Response containing detected faces without identity."""

    faces: list[DetectedFace] = Field(default_factory=list)
    face_count: int = Field(..., description="Number of faces detected")
