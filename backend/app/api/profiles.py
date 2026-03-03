"""API endpoints for user profiles."""

import asyncio
import logging
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel

from app.auth import CurrentUser, get_current_user
from app.config import get_settings
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
from app.services import (
    LinkedInEnrichmentError,
    LinkedInEnrichmentService,
    ProfileImageError,
    ProfileImageService,
    ProfileSummaryService,
    calculate_profile_completion,
)
from app.services.resume_parser import ResumeData, ResumeParser
from app.utils.s3_helpers import upload_profile_picture

logger = logging.getLogger(__name__)

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

    created_profile = await dal.create(current_user.id, data)
    return await _refresh_generated_profile_summary(dal, created_profile)


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
    return await _refresh_generated_profile_summary(dal, profile)


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

    saved_profile = await _refresh_generated_profile_summary(dal, saved_profile)

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


# =============================================================================
# Resume Upload & Parsing
# =============================================================================


class ResumeParseResponse(BaseModel):
    """Response from resume parsing endpoint."""

    message: str
    extracted_data: dict
    profile_updated: bool


@router.post("/me/resume", response_model=ResumeParseResponse)
async def upload_resume(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    dal: Annotated[ProfileDAL, Depends(get_profile_dal)],
    file: UploadFile = File(..., description="Resume file (PDF or DOCX)"),
) -> ResumeParseResponse:
    """
    Upload a resume to extract profile information.

    Parses the resume and updates the user's profile with extracted data.
    Supported formats: PDF, DOCX

    If OpenAI API key is configured, uses AI for smarter extraction.
    Otherwise, falls back to pattern-based extraction.
    """
    # Validate file type
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required",
        )

    allowed_extensions = (".pdf", ".docx", ".doc")
    if not file.filename.lower().endswith(allowed_extensions):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}",
        )

    # Check file size (max 10MB)
    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File too large. Maximum size is 10MB.",
        )

    # Reset file position for parsing
    await file.seek(0)

    # Parse the resume
    settings = get_settings()
    parser = ResumeParser(openai_api_key=settings.openai_api_key)

    try:
        resume_data: ResumeData = parser.parse(contents, file.filename)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Resume parsing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to parse resume. Please try again or use a different format.",
        )

    # Validate extracted data has minimum required content
    if not resume_data.full_name and not resume_data.raw_text:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Could not extract any information from the resume. "
            "Please ensure the file contains readable text.",
        )

    # Use admin client to bypass RLS for profile creation/update
    from app.db.supabase import get_admin_client

    admin_client = get_admin_client()

    # Check if profile exists using admin client
    try:
        existing_response = (
            admin_client.table("profiles")
            .select("user_id")
            .eq("user_id", str(current_user.id))
            .execute()
        )
        existing_profile = existing_response.data and len(existing_response.data) > 0
    except Exception as e:
        logger.error(f"Database query failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error. Please try again.",
        )

    profile_updated = False
    if existing_profile:
        # Update existing profile (only non-None fields)
        update_data: dict[str, Any] = {}
        if resume_data.full_name:
            update_data["full_name"] = _truncate_string(resume_data.full_name, 255)
        if resume_data.headline:
            update_data["headline"] = _truncate_string(resume_data.headline, 255)
        if resume_data.bio:
            update_data["bio"] = _truncate_string(resume_data.bio, 2000)
        if resume_data.company:
            update_data["company"] = _truncate_string(resume_data.company, 255)
        if resume_data.major:
            update_data["major"] = _truncate_string(resume_data.major, 255)
        if resume_data.graduation_year:
            update_data["graduation_year"] = resume_data.graduation_year
        if resume_data.location:
            update_data["location"] = _truncate_string(resume_data.location, 255)
        if resume_data.profile_one_liner:
            update_data["profile_one_liner"] = _truncate_string(resume_data.profile_one_liner, 500)
        if resume_data.profile_summary:
            update_data["profile_summary"] = _truncate_string(resume_data.profile_summary, 5000)
        if resume_data.experiences:
            update_data["experiences"] = resume_data.experiences
        if resume_data.education:
            update_data["education"] = resume_data.education

        if update_data:
            try:
                admin_client.table("profiles").update(update_data).eq(
                    "user_id", str(current_user.id)
                ).execute()
                profile_updated = True
            except Exception as e:
                logger.error(f"Failed to update profile: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to update profile. Please try again.",
                )
    else:
        # Create new profile using admin client
        profile_data: dict[str, Any] = {
            "user_id": str(current_user.id),
            "full_name": _truncate_string(resume_data.full_name, 255) or "Unknown",
            "headline": _truncate_string(resume_data.headline, 255),
            "bio": _truncate_string(resume_data.bio, 2000),
            "company": _truncate_string(resume_data.company, 255),
            "major": _truncate_string(resume_data.major, 255),
            "graduation_year": resume_data.graduation_year,
            "location": _truncate_string(resume_data.location, 255),
            "profile_one_liner": _truncate_string(resume_data.profile_one_liner, 500),
            "profile_summary": _truncate_string(resume_data.profile_summary, 5000),
            "experiences": resume_data.experiences or [],
            "education": resume_data.education or [],
        }
        # Remove None values
        profile_data = {k: v for k, v in profile_data.items() if v is not None}
        try:
            admin_client.table("profiles").insert(profile_data).execute()
            profile_updated = True
        except Exception as e:
            logger.error(f"Failed to create profile: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create profile. Please try again.",
            )

    # Build response with extracted data
    extracted: dict[str, Any] = {
        "full_name": resume_data.full_name,
        "headline": resume_data.headline,
        "bio": resume_data.bio,
        "company": resume_data.company,
        "major": resume_data.major,
        "graduation_year": resume_data.graduation_year,
        "location": resume_data.location,
        "email": resume_data.email,
        "phone": resume_data.phone,
        "skills": resume_data.skills,
        "profile_one_liner": resume_data.profile_one_liner,
        "profile_summary": resume_data.profile_summary,
        "experiences": resume_data.experiences,
        "education": resume_data.education,
    }

    return ResumeParseResponse(
        message="Resume parsed successfully",
        extracted_data={k: v for k, v in extracted.items() if v is not None},
        profile_updated=profile_updated,
    )


# =============================================================================
# Helper Functions
# =============================================================================


def _truncate_string(value: str | None, max_length: int) -> str | None:
    """Truncate string to max length, returning None for empty strings."""
    if value is None:
        return None
    if not isinstance(value, str):
        value = str(value)
    value = value.strip()
    if not value:
        return None
    if len(value) > max_length:
        return value[:max_length]
    return value


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


async def _refresh_generated_profile_summary(
    dal: ProfileDAL,
    profile: ProfileResponse,
) -> ProfileResponse:
    """Regenerate AI/profile summaries whenever profile data changes."""
    summary_service = ProfileSummaryService()
    try:
        generated = await asyncio.to_thread(summary_service.generate, profile)
        updated = await dal.update_generated_summary(
            profile.user_id,
            profile_one_liner=generated.one_liner,
            profile_summary=generated.summary,
            summary_provider=generated.provider,
        )
        return updated or profile
    except Exception as exc:
        if get_settings().profile_summary_provider.strip().lower() == "dspy":
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Profile summary generation failed: {exc}",
            )
        return profile
