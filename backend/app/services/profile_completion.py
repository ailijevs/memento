"""Utilities for computing profile completion state."""

from app.schemas.profile import ProfileResponse
from app.schemas.profile_completion import ProfileCompletionResponse, RequiredField

_REQUIRED_FIELDS: list[RequiredField] = [
    "name",
    "location",
    "experiences",
    "profile_pic",
    "education",
    "bio",
]


def calculate_profile_completion(profile: ProfileResponse) -> ProfileCompletionResponse:
    """Compute completion state for required profile fields."""
    missing_fields: list[RequiredField] = []

    if not profile.full_name or not profile.full_name.strip():
        missing_fields.append("name")
    if not profile.location or not profile.location.strip():
        missing_fields.append("location")
    if not profile.experiences:
        missing_fields.append("experiences")
    if not profile.photo_path or not profile.photo_path.strip():
        missing_fields.append("profile_pic")
    if not profile.education:
        missing_fields.append("education")
    if not profile.bio or not profile.bio.strip():
        missing_fields.append("bio")

    completed = len(_REQUIRED_FIELDS) - len(missing_fields)
    score = int(round((completed / len(_REQUIRED_FIELDS)) * 100))

    return ProfileCompletionResponse(
        is_complete=len(missing_fields) == 0,
        completion_score=score,
        missing_fields=missing_fields,
    )
