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
    """Frontend-friendly profile card for a recognized person.

    Condensed view: full_name, headline, company, photo_path, face_similarity.
    Detail view: all fields including bio, experiences, education, linkedin_url.
    """

    user_id: str = Field(..., description="Matched user UUID")
    # Condensed card fields
    full_name: str = Field(..., description="Person's full name")
    headline: str | None = Field(None, description="Professional headline")
    company: str | None = Field(None, description="Current company")
    photo_path: str | None = Field(None, description="Profile photo storage key")
    profile_one_liner: str | None = Field(None, description="One-line summary")
    face_similarity: float = Field(
        ...,
        ge=0,
        le=100,
        description="Rekognition face match confidence between "
        "the captured image and the user's indexed profile photo",
    )
    experience_similarity: float | None = Field(
        None,
        ge=0,
        le=100,
        description="Similarity score between the current user's "
        "experiences and the matched user's experiences",
    )
    # Detail view fields
    bio: str | None = Field(None, description="Short bio")
    location: str | None = Field(None, description="City, State or City, Country")
    major: str | None = Field(None, description="Field of study")
    graduation_year: int | None = Field(None, description="Year of graduation")
    linkedin_url: str | None = Field(None, description="LinkedIn profile URL")
    profile_summary: str | None = Field(None, description="Multi-sentence summary")
    experiences: list[dict] | None = Field(None, description="Work experience entries")
    education: list[dict] | None = Field(None, description="Education entries")


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
