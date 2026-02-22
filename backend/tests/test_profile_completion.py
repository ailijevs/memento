"""Tests for profile completion calculation."""

from datetime import datetime, timezone
from uuid import uuid4

from app.schemas.profile import ProfileResponse
from app.services.profile_completion import calculate_profile_completion


def _make_profile(**overrides) -> ProfileResponse:
    base = {
        "user_id": uuid4(),
        "full_name": "Test User",
        "headline": "Engineer",
        "bio": "Building things",
        "location": "West Lafayette, Indiana, United States",
        "company": "Acme",
        "major": "Computer Engineering",
        "graduation_year": 2026,
        "linkedin_url": "https://www.linkedin.com/in/test-user/",
        "photo_path": "profile_images/test.jpg",
        "experiences": [{"title": "Engineer", "company": "Acme"}],
        "education": [{"school": "Purdue University"}],
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    base.update(overrides)
    return ProfileResponse(**base)


def test_profile_completion_all_required_fields_present():
    """Complete profiles should report 100% completion."""
    profile = _make_profile()
    completion = calculate_profile_completion(profile)

    assert completion.is_complete is True
    assert completion.completion_score == 100
    assert completion.missing_fields == []


def test_profile_completion_reports_missing_required_fields():
    """Missing required fields should be surfaced in completion response."""
    profile = _make_profile(
        location=None,
        bio=None,
        experiences=[],
        education=[],
        photo_path=None,
    )

    completion = calculate_profile_completion(profile)

    assert completion.is_complete is False
    assert completion.completion_score == 17
    assert set(completion.missing_fields) == {
        "location",
        "bio",
        "experiences",
        "education",
        "profile_pic",
    }
