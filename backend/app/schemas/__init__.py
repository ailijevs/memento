"""Pydantic schemas for request/response validation."""

from .analytics import (
    AttendeeEventAnalytics,
    AttendeeExportRow,
    AttendeeOverview,
    ConsentBreakdown,
    EventAnalytics,
    EventComparison,
    EventQuickStats,
    LiveEventStatus,
    OrganizerOverview,
    PostEventReport,
    TimeSeriesBucket,
    TopRecognizedUser,
)
from .consent import (
    ConsentCreate,
    ConsentResponse,
    ConsentUpdate,
)
from .event import (
    EventCreate,
    EventProcessingStatus,
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
    ProfileDirectoryResponse,
    ProfileResponse,
    ProfileUpdate,
)
from .profile_completion import ProfileCompletionResponse
from .recognition import (
    FaceMatch,
    FrameDetectionRequest,
    FrameDetectionResponse,
    ProfileCard,
)

__all__ = [
    # Consent
    "ConsentCreate",
    "ConsentResponse",
    "ConsentUpdate",
    # Event
    "EventCreate",
    "EventProcessingStatus",
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
    "ProfileDirectoryResponse",
    "ProfileResponse",
    "ProfileUpdate",
    # Recognition
    "FaceMatch",
    "FrameDetectionRequest",
    "FrameDetectionResponse",
    "ProfileCard",
    # Analytics
    "AttendeeEventAnalytics",
    "AttendeeExportRow",
    "AttendeeOverview",
    "ConsentBreakdown",
    "EventAnalytics",
    "EventComparison",
    "EventQuickStats",
    "LiveEventStatus",
    "OrganizerOverview",
    "PostEventReport",
    "TimeSeriesBucket",
    "TopRecognizedUser",
]
