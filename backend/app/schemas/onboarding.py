"""Schemas for onboarding flows."""

from pydantic import BaseModel, Field

from .linkedin_enrichment import LinkedInEnrichmentResponse
from .profile import ProfileResponse
from .profile_completion import ProfileCompletionResponse


class LinkedInOnboardingRequest(BaseModel):
    """Request payload for fully automatic LinkedIn onboarding."""

    linkedin_url: str = Field(..., min_length=10, max_length=500)
    provider: str = Field(default="auto", min_length=2, max_length=20)


class LinkedInOnboardingResponse(BaseModel):
    """Response for LinkedIn onboarding pipeline."""

    profile: ProfileResponse
    enrichment: LinkedInEnrichmentResponse
    completion: ProfileCompletionResponse
    image_saved: bool = False
