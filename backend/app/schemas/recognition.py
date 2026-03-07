"""Pydantic schemas for facial recognition operations."""

from uuid import UUID

from pydantic import BaseModel, Field


class FaceMatch(BaseModel):
    """A matched face from the recognition collection (internal use)."""

    user_id: str | None = Field(None, description="User UUID if face is registered")
    face_id: str = Field(..., description="Rekognition face ID")
    similarity: float = Field(..., ge=0, le=100, description="Match confidence %")
    confidence: float = Field(..., ge=0, le=100, description="Detection confidence %")


class ProfileCard(BaseModel):
    """Frontend-friendly profile card for a recognized person."""

    user_id: str = Field(..., description="Matched user UUID")
    full_name: str = Field(..., description="Person's full name")
    headline: str | None = Field(None, description="Professional headline")
    bio: str | None = Field(None, description="Short bio")
    company: str | None = Field(None, description="Current company")
    photo_path: str | None = Field(None, description="Profile photo storage key")
    linkedin_url: str | None = Field(None, description="LinkedIn profile URL")
    profile_one_liner: str | None = Field(None, description="One-line summary")
    similarity: float = Field(..., ge=0, le=100, description="Match confidence %")


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
    """Response containing profile cards for identified faces."""

    matches: list[ProfileCard] = Field(
        default_factory=list,
        description="Profile cards for identified people",
    )
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")
    event_id: UUID | None = None
