"""Pydantic schemas for request/response validation."""

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
from .notification import (
    NotificationLogCreate,
    NotificationLogResponse,
    NotificationPreferenceResponse,
    NotificationPreferenceUpdate,
    NotificationStatus,
    NotificationType,
)
from .onboarding import (
    LinkedInOnboardingRequest,
    LinkedInOnboardingResponse,
)
from .profile import (
    ProfileCreate,
    ProfileDirectoryEntry,
    ProfileDirectoryResponse,
    ProfilePhotoUploadConfirmRequest,
    ProfilePhotoUploadUrlRequest,
    ProfilePhotoUploadUrlResponse,
    ProfilePhotoUrlResponse,
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
    # Notification
    "NotificationLogCreate",
    "NotificationLogResponse",
    "NotificationPreferenceResponse",
    "NotificationPreferenceUpdate",
    "NotificationStatus",
    "NotificationType",
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
    "ProfilePhotoUploadConfirmRequest",
    "ProfilePhotoUrlResponse",
    "ProfilePhotoUploadUrlRequest",
    "ProfilePhotoUploadUrlResponse",
    "ProfileResponse",
    "ProfileUpdate",
    # Recognition
    "FaceMatch",
    "FrameDetectionRequest",
    "FrameDetectionResponse",
    "ProfileCard",
]
