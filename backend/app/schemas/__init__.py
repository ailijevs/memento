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
from .linkedin_enrichment import (
    EducationItem,
    ExperienceItem,
    LinkedInEnrichmentRequest,
    LinkedInEnrichmentResponse,
)
from .membership import (
    MembershipCreate,
    MembershipResponse,
    MembershipRole,
    MembershipUpdate,
)
from .onboarding import (
    LinkedInOnboardingRequest,
    LinkedInOnboardingResponse,
)
from .profile import (
    ProfileCreate,
    ProfileDirectoryEntry,
    ProfileResponse,
    ProfileUpdate,
)
from .profile_completion import ProfileCompletionResponse

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
