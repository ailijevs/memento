"""Pydantic schemas for request/response validation."""

from .consent import (
    ConsentCreate,
    ConsentResponse,
    ConsentUpdate,
)
from .event import (
    EventCreate,
    EventResponse,
    EventUpdate,
)
from .membership import (
    MembershipCreate,
    MembershipResponse,
    MembershipRole,
    MembershipUpdate,
)
from .linkedin_enrichment import (
    EducationItem,
    ExperienceItem,
    LinkedInEnrichmentRequest,
    LinkedInEnrichmentResponse,
)
from .onboarding import (
    LinkedInOnboardingRequest,
    LinkedInOnboardingResponse,
)
from .profile_completion import ProfileCompletionResponse
from .profile import (
    ProfileCreate,
    ProfileDirectoryEntry,
    ProfileResponse,
    ProfileUpdate,
)

__all__ = [
    # Consent
    "ConsentCreate",
    "ConsentResponse",
    "ConsentUpdate",
    # Event
    "EventCreate",
    "EventResponse",
    "EventUpdate",
    # Membership
    "MembershipCreate",
    "MembershipResponse",
    "MembershipRole",
    "MembershipUpdate",
    # LinkedIn Enrichment
    "EducationItem",
    "ExperienceItem",
    "LinkedInEnrichmentRequest",
    "LinkedInEnrichmentResponse",
    "LinkedInOnboardingRequest",
    "LinkedInOnboardingResponse",
    "ProfileCompletionResponse",
    # Profile
    "ProfileCreate",
    "ProfileDirectoryEntry",
    "ProfileResponse",
    "ProfileUpdate",
]
