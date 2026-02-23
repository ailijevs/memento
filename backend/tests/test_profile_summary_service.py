"""Tests for profile summary generation service."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import pytest

from app.schemas import ProfileResponse
from app.services.profile_summary import ProfileSummaryError, ProfileSummaryService


@dataclass
class _SettingsStub:
    profile_summary_provider: str = "auto"
    profile_summary_model: str = "openai/gpt-4o-mini"
    openai_api_key: str | None = None


def _make_profile(**overrides: Any) -> ProfileResponse:
    base: dict[str, Any] = {
        "user_id": uuid4(),
        "full_name": "Alex Smith",
        "headline": "Software Engineer",
        "bio": "Builds backend APIs for developer tools.",
        "location": "Austin, Texas, United States",
        "company": "Acme Labs",
        "major": "Computer Engineering",
        "graduation_year": 2026,
        "linkedin_url": "https://www.linkedin.com/in/alex-smith/",
        "photo_path": None,
        "experiences": [{"title": "Software Engineer", "company": "Acme Labs"}],
        "education": [{"school": "Purdue University", "degree": "BS"}],
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    base.update(overrides)
    return ProfileResponse(**base)


def test_template_provider_generates_non_empty_summary_fields():
    service = ProfileSummaryService(settings=_SettingsStub(profile_summary_provider="template"))

    result = service.generate(_make_profile())

    assert result.provider == "template"
    assert "Alex Smith" in result.one_liner
    assert len(result.one_liner) > 10
    assert len(result.summary) > 20


def test_auto_provider_falls_back_to_template_without_openai_key():
    service = ProfileSummaryService(settings=_SettingsStub(profile_summary_provider="auto"))

    result = service.generate(_make_profile())

    assert result.provider == "template"
    assert result.one_liner
    assert result.summary


def test_dspy_provider_requires_openai_api_key():
    service = ProfileSummaryService(settings=_SettingsStub(profile_summary_provider="dspy"))

    with pytest.raises(ProfileSummaryError):
        service.generate(_make_profile())
