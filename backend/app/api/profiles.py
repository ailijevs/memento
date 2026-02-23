"""API endpoints for user profiles."""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel

from app.auth import CurrentUser, get_current_user
from app.config import get_settings
from app.dals import ProfileDAL
from app.db import get_supabase_client
from app.schemas import (
    ProfileCreate,
    ProfileDirectoryEntry,
    ProfileResponse,
    ProfileUpdate,
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
        import io

        file_content = io.BytesIO(contents)
        resume_data: ResumeData = await parser.parse(file_content, file.filename)
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

    profile_updated = False
    if existing_profile:
        # Update existing profile (only non-None fields)
        update_data = {}
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
        if resume_data.graduation_year:
            update_data["graduation_year"] = str(resume_data.graduation_year)

        if update_data:
            admin_client.table("profiles").update(update_data).eq(
                "user_id", str(current_user.id)
            ).execute()
            profile_updated = True
    else:
        # Create new profile using admin client
        profile_data = {
            "user_id": str(current_user.id),
            "full_name": resume_data.full_name or "Unknown",
            "headline": resume_data.headline,
            "bio": resume_data.bio,
            "company": resume_data.company,
            "major": resume_data.major,
            "graduation_year": resume_data.graduation_year,
        }
        # Remove None values
        profile_data = {k: v for k, v in profile_data.items() if v is not None}
        admin_client.table("profiles").insert(profile_data).execute()
        profile_updated = True

    # Build response with extracted data
    extracted = {
        "full_name": resume_data.full_name,
        "headline": resume_data.headline,
        "bio": resume_data.bio,
        "company": resume_data.company,
        "major": resume_data.major,
        "graduation_year": resume_data.graduation_year,
        "email": resume_data.email,
        "phone": resume_data.phone,
        "skills": resume_data.skills,
    }

    return ResumeParseResponse(
        message="Resume parsed successfully",
        extracted_data={k: v for k, v in extracted.items() if v is not None},
        profile_updated=profile_updated,
    )
