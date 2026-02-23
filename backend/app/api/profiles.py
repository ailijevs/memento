"""API endpoints for user profiles."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import CurrentUser, get_current_user
from app.dals import ProfileDAL
from app.db import get_supabase_client
from app.schemas import (
    LinkedInEnrichmentRequest,
    LinkedInEnrichmentResponse,
    LinkedInOnboardingRequest,
    LinkedInOnboardingResponse,
    ProfileCompletionResponse,
    ProfileCreate,
    ProfileDirectoryEntry,
    ProfileResponse,
    ProfileUpdate,
)
from app.config import get_settings
from app.services import (
    LinkedInEnrichmentError,
    LinkedInEnrichmentService,
    ProfileImageError,
    ProfileImageService,
    calculate_profile_completion,
)
from app.utils.s3_helpers import upload_profile_picture

router = APIRouter(prefix="/profiles", tags=["profiles"])


def get_profile_dal(current_user: Annotated[CurrentUser, Depends(get_current_user)]) -> ProfileDAL:
    """Dependency to get ProfileDAL with authenticated client."""
    client = get_supabase_client(current_user.access_token)
    return ProfileDAL(client)


@router.get("/me", response_model=ProfileResponse)
async def get_my_profile(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    dal: Annotated[ProfileDAL, Depends(get_profile_dal)],
) -> ProfileResponse:
    """Get the current user's profile."""
    profile = await dal.get_by_user_id(current_user.id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found. Please create one first.",
        )
    return profile


@router.get("/me/completion", response_model=ProfileCompletionResponse)
async def get_my_profile_completion(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    dal: Annotated[ProfileDAL, Depends(get_profile_dal)],
) -> ProfileCompletionResponse:
    """Get completion state for the current user's profile."""
    profile = await dal.get_by_user_id(current_user.id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found. Please create one first.",
        )
    return calculate_profile_completion(profile)


@router.post("/me", response_model=ProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_my_profile(
    data: ProfileCreate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    dal: Annotated[ProfileDAL, Depends(get_profile_dal)],
) -> ProfileResponse:
    """Create the current user's profile."""
    # Check if profile already exists
    existing = await dal.get_by_user_id(current_user.id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Profile already exists. Use PATCH to update.",
        )

    return await dal.create(current_user.id, data)


@router.patch("/me", response_model=ProfileResponse)
async def update_my_profile(
    data: ProfileUpdate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    dal: Annotated[ProfileDAL, Depends(get_profile_dal)],
) -> ProfileResponse:
    """Update the current user's profile."""
    profile = await dal.update(current_user.id, data)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found. Please create one first.",
        )
    return profile


@router.post("/enrich-linkedin", response_model=LinkedInEnrichmentResponse)
async def enrich_linkedin_profile(
    data: LinkedInEnrichmentRequest,
    _: Annotated[CurrentUser, Depends(get_current_user)],
) -> LinkedInEnrichmentResponse:
    """
    Enrich profile data from a LinkedIn URL using configured third-party providers.
    Requires authentication to avoid exposing this as an anonymous open proxy.
    """
    service = LinkedInEnrichmentService()

    try:
        result = await service.enrich_profile(
            linkedin_url=data.linkedin_url,
            provider=data.provider,
        )
    except LinkedInEnrichmentError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)

    return LinkedInEnrichmentResponse(**result)


@router.post("/onboard-from-linkedin-url", response_model=LinkedInOnboardingResponse)
async def onboard_from_linkedin_url(
    data: LinkedInOnboardingRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    dal: Annotated[ProfileDAL, Depends(get_profile_dal)],
) -> LinkedInOnboardingResponse:
    """
    End-to-end onboarding from LinkedIn URL:
    enrich profile data, save profile image JPEG, then create/update profile.
    """
    enrichment_service = LinkedInEnrichmentService()
    image_service = ProfileImageService()
    settings = get_settings()

    try:
        enrichment_result = await enrichment_service.enrich_profile(
            linkedin_url=data.linkedin_url,
            provider=data.provider,
        )
    except LinkedInEnrichmentError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)

    enrichment = LinkedInEnrichmentResponse(**enrichment_result)
    if not enrichment.full_name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Unable to extract full name from LinkedIn URL.",
        )

    first_experience = enrichment.experiences[0] if enrichment.experiences else None
    first_education = enrichment.education[0] if enrichment.education else None

    photo_path: str | None = None
    image_saved = False
    if enrichment.profile_image_url:
        try:
            raw_image_bytes = await image_service.fetch_image_bytes(enrichment.profile_image_url)
            if not settings.s3_bucket_name:
                raise ProfileImageError(
                    "S3_BUCKET_NAME must be configured to upload profile pictures."
                )
            photo_path = upload_profile_picture(
                user_id=current_user.id,
                image=raw_image_bytes,
                bucket_name=settings.s3_bucket_name,
                source="linkedin",
            )
            image_saved = True
        except (ProfileImageError, RuntimeError, ValueError):
            photo_path = None
            image_saved = False

    existing = await dal.get_by_user_id(current_user.id)
    if existing:
        saved_profile = await dal.update(
            current_user.id,
            ProfileUpdate(
                full_name=enrichment.full_name,
                headline=enrichment.headline,
                bio=enrichment.bio,
                location=enrichment.location,
                company=first_experience.company if first_experience else None,
                major=first_education.field_of_study if first_education else None,
                graduation_year=_parse_graduation_year(
                    first_education.end_date if first_education else None
                ),
                linkedin_url=enrichment.linkedin_url,
                photo_path=photo_path or existing.photo_path,
                experiences=[item.model_dump() for item in enrichment.experiences],
                education=[item.model_dump() for item in enrichment.education],
            ),
        )
        if saved_profile is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Profile update failed."
            )
    else:
        saved_profile = await dal.create(
            current_user.id,
            ProfileCreate(
                full_name=enrichment.full_name,
                headline=enrichment.headline,
                bio=enrichment.bio,
                location=enrichment.location,
                company=first_experience.company if first_experience else None,
                major=first_education.field_of_study if first_education else None,
                graduation_year=_parse_graduation_year(
                    first_education.end_date if first_education else None
                ),
                linkedin_url=enrichment.linkedin_url,
                photo_path=photo_path,
                experiences=[item.model_dump() for item in enrichment.experiences],
                education=[item.model_dump() for item in enrichment.education],
            ),
        )

    return LinkedInOnboardingResponse(
        profile=saved_profile,
        enrichment=enrichment,
        completion=calculate_profile_completion(saved_profile),
        image_saved=image_saved,
    )


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_profile(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    dal: Annotated[ProfileDAL, Depends(get_profile_dal)],
) -> None:
    """Delete the current user's profile."""
    deleted = await dal.delete(current_user.id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found.",
        )


@router.get("/{user_id}", response_model=ProfileResponse)
async def get_profile(
    user_id: UUID,
    dal: Annotated[ProfileDAL, Depends(get_profile_dal)],
) -> ProfileResponse:
    """
    Get another user's profile.
    RLS enforces: only visible if you share an event and they consented.
    """
    profile = await dal.get_by_user_id(user_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found or not visible.",
        )
    return profile


@router.get("/directory/{event_id}", response_model=list[ProfileDirectoryEntry])
async def get_event_directory(
    event_id: UUID,
    dal: Annotated[ProfileDAL, Depends(get_profile_dal)],
) -> list[ProfileDirectoryEntry]:
    """
    Get the directory of profiles for an event.
    Only returns profiles of users who have consented to display.
    Uses the get_event_directory SQL function.
    """
    return await dal.get_event_directory(event_id)


def _parse_graduation_year(end_date: str | None) -> int | None:
    """Best-effort parser for YYYY or YYYY-MM date strings."""
    if not end_date:
        return None
    cleaned = end_date.strip()
    if len(cleaned) >= 4 and cleaned[:4].isdigit():
        year = int(cleaned[:4])
        if 1900 <= year <= 2100:
            return year
    return None
