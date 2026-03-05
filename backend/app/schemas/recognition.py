"""Pydantic schemas for facial recognition operations."""

from uuid import UUID

from pydantic import BaseModel, Field


class BoundingBox(BaseModel):
    """Bounding box coordinates for a detected face."""

    width: float = Field(..., ge=0, le=1, description="Width as fraction of image")
    height: float = Field(..., ge=0, le=1, description="Height as fraction of image")
    left: float = Field(..., ge=0, le=1, description="Left position as fraction")
    top: float = Field(..., ge=0, le=1, description="Top position as fraction of image")


class FaceMatch(BaseModel):
    """A matched face from the recognition collection."""

    user_id: str | None = Field(None, description="User UUID if face is registered")
    face_id: str = Field(..., description="Rekognition face ID")
    similarity: float = Field(..., ge=0, le=100, description="Match confidence %")
    confidence: float = Field(..., ge=0, le=100, description="Detection confidence %")


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


class FrameDetectionResponse(BaseModel):
    """Response containing identified faces from a frame."""

    matches: list[FaceMatch] = Field(
        default_factory=list,
        description="List of identified faces",
    )
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")
    event_id: UUID | None = None
