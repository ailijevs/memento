"""Schemas for profile completion tracking."""

from typing import Literal

from pydantic import BaseModel, Field

RequiredField = Literal[
    "name",
    "location",
    "experiences",
    "profile_pic",
    "education",
    "bio",
]


class ProfileCompletionResponse(BaseModel):
    """Represents completion state for required profile fields."""

    is_complete: bool
    completion_score: int = Field(..., ge=0, le=100)
    missing_fields: list[RequiredField] = Field(default_factory=list)
