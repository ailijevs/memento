"""API endpoints for user profiles."""

import asyncio
import ipaddress
import logging
from typing import Annotated, Any
from urllib.parse import urlparse
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
    CompatibilityResult,
    CompatibilityService,
    LinkedInEnrichmentError,
    LinkedInEnrichmentService,
    ProfileImageError,
    ProfileImageService,
    ProfileSummaryService,
    S3Service,
    calculate_profile_completion,
)
from app.services.resume_parser import ResumeData, ResumeParser

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
    if enrichment.profile_image_url and _is_safe_image_url(enrichment.profile_image_url):
        try:
            raw_image_bytes = await image_service.fetch_image_bytes(enrichment.profile_image_url)
            if not settings.s3_bucket_name:
                raise ProfileImageError(
                    "S3_BUCKET_NAME must be configured to upload profile pictures."
                )
            s3_service = S3Service()
            photo_path = s3_service.upload_profile_picture(
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
                full_name=existing.full_name or _title_case_name(enrichment.full_name),
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
                full_name=_title_case_name(enrichment.full_name),
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


class CompatibilityResponse(BaseModel):
    """Compatibility score and conversation starters between two users."""

    score: float
    shared_companies: list[str]
    shared_schools: list[str]
    shared_fields: list[str]
    conversation_starters: list[str]


@router.get("/{user_id}/compatibility", response_model=CompatibilityResponse)
async def get_compatibility(
    user_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    dal: Annotated[ProfileDAL, Depends(get_profile_dal)],
) -> CompatibilityResponse:
    """
    Compute a compatibility score between the current user and another user,
    and generate conversation starters based on shared background.
    """
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot compute compatibility with yourself.",
        )

    viewer_profile = await dal.get_by_user_id(current_user.id)
    if not viewer_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Your profile was not found. Please create one first.",
        )

    target_profile = await dal.get_by_user_id(user_id)
    if not target_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target profile not found or not visible.",
        )

    result: CompatibilityResult = await asyncio.to_thread(
        CompatibilityService().compute, viewer_profile, target_profile
    )

    return CompatibilityResponse(
        score=result.score,
        shared_companies=result.shared_companies,
        shared_schools=result.shared_schools,
        shared_fields=result.shared_fields,
        conversation_starters=result.conversation_starters,
    )


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

    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File too large. Maximum size is 10MB.",
        )

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

    # Use admin client to bypass RLS for profile creation/update
    from app.db.supabase import get_admin_client

    admin_client = get_admin_client()

    # Check if profile exists using admin client
    existing_response = (
        admin_client.table("profiles")
        .select("user_id")
        .eq("user_id", str(current_user.id))
        .execute()
    )
    existing_profile = existing_response.data and len(existing_response.data) > 0

    # Safely coerce graduation_year to int (AI parsers sometimes return strings)
    grad_year: int | None = None
    if resume_data.graduation_year is not None:
        try:
            grad_year = int(resume_data.graduation_year)
        except (ValueError, TypeError):
            grad_year = None

    profile_updated = False
    try:
        if existing_profile:
            update_data: dict[str, Any] = {}
            if resume_data.full_name:
                update_data["full_name"] = resume_data.full_name
            if resume_data.headline:
                update_data["headline"] = resume_data.headline
            if resume_data.bio:
                update_data["bio"] = resume_data.bio
            if resume_data.company:
                update_data["company"] = resume_data.company
            if resume_data.major:
                update_data["major"] = resume_data.major
            if grad_year:
                update_data["graduation_year"] = grad_year
            if resume_data.location:
                update_data["location"] = resume_data.location
            if resume_data.profile_one_liner:
                update_data["profile_one_liner"] = resume_data.profile_one_liner
            if resume_data.profile_summary:
                update_data["profile_summary"] = resume_data.profile_summary
            if resume_data.experiences:
                update_data["experiences"] = resume_data.experiences
            if resume_data.education:
                update_data["education"] = resume_data.education

            if update_data:
                admin_client.table("profiles").update(update_data).eq(
                    "user_id", str(current_user.id)
                ).execute()
                profile_updated = True
        else:
            profile_data = {
                "user_id": str(current_user.id),
                "full_name": resume_data.full_name or "Unknown",
                "headline": resume_data.headline,
                "bio": resume_data.bio,
                "company": resume_data.company,
                "major": resume_data.major,
                "graduation_year": grad_year,
                "location": resume_data.location,
                "profile_one_liner": resume_data.profile_one_liner,
                "profile_summary": resume_data.profile_summary,
                "experiences": resume_data.experiences,
                "education": resume_data.education,
            }
            profile_data = {k: v for k, v in profile_data.items() if v is not None}
            admin_client.table("profiles").insert(profile_data).execute()
            profile_updated = True
    except Exception as e:
        logger.error(f"Resume profile save failed: {e}")

    extracted = {
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


def _title_case_name(name: str) -> str:
    """Title-case a name string, e.g. 'aleksandar ilijevski' → 'Aleksandar Ilijevski'."""
    return name.strip().title()


def _is_safe_image_url(url: str) -> bool:
    """Return True only for https URLs pointing to a public, non-private host."""
    try:
        parsed = urlparse(url.strip())
    except Exception:
        return False

    if parsed.scheme != "https":
        return False

    host = parsed.hostname or ""
    if not host:
        return False

    if host in ("localhost", "127.0.0.1", "::1"):
        return False

    try:
        addr = ipaddress.ip_address(host)
        if addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved:
            return False
    except ValueError:
        pass  # domain name, not an IP — fine

    return True



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
