"""Pydantic schemas for user profiles."""
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


class ProfileBase(BaseModel):
    """Base profile fields."""

    full_name: str = Field(..., min_length=1, max_length=255)
    headline: str | None = Field(None, max_length=255)
    bio: str | None = Field(None, max_length=2000)
    company: str | None = Field(None, max_length=255)
    major: str | None = Field(None, max_length=255)
    graduation_year: int | None = Field(None, ge=1900, le=2100)
    linkedin_url: str | None = Field(None, max_length=500)
    photo_path: str | None = Field(None, max_length=500)


class ProfileCreate(ProfileBase):
    """Schema for creating a new profile."""

    pass


class ProfileUpdate(BaseModel):
    """Schema for updating a profile. All fields optional."""

    full_name: str | None = Field(None, min_length=1, max_length=255)
    headline: str | None = Field(None, max_length=255)
    bio: str | None = Field(None, max_length=2000)
    company: str | None = Field(None, max_length=255)
    major: str | None = Field(None, max_length=255)
    graduation_year: int | None = Field(None, ge=1900, le=2100)
    linkedin_url: str | None = Field(None, max_length=500)
    photo_path: str | None = Field(None, max_length=500)


class ProfileResponse(ProfileBase):
    """Schema for profile responses."""

    user_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProfileDirectoryEntry(BaseModel):
    """
    Lightweight profile for event directory listing.
    Matches the get_event_directory SQL function return type.
    """

    user_id: UUID
    full_name: str
    headline: str | None = None
    company: str | None = None
    photo_path: str | None = None

    class Config:
        from_attributes = True
