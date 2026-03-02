"""Schemas for LinkedIn profile enrichment."""

from typing import Any

from pydantic import BaseModel, Field


class ExperienceItem(BaseModel):
    """Normalized work experience entry."""

    title: str | None = None
    company: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    description: str | None = None


class EducationItem(BaseModel):
    """Normalized education entry."""

    school: str | None = None
    degree: str | None = None
    field_of_study: str | None = None
    start_date: str | None = None
    end_date: str | None = None


class LinkedInEnrichmentRequest(BaseModel):
    """Request payload for LinkedIn URL enrichment."""

    linkedin_url: str = Field(..., min_length=10, max_length=500)
    provider: str = Field(default="auto", min_length=2, max_length=20)


class LinkedInEnrichmentResponse(BaseModel):
    """Normalized enrichment response."""

    full_name: str | None = None
    bio: str | None = None
    headline: str | None = None
    location: str | None = None
    experiences: list[ExperienceItem] = Field(default_factory=list)
    education: list[EducationItem] = Field(default_factory=list)
    profile_image_url: str | None = None
    linkedin_url: str
    source: str
    confidence: float | None = None
    raw_payload: dict[str, Any] = Field(default_factory=dict)
