"""Unit tests for CompatibilityService and its helper functions."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4

from app.schemas import ProfileResponse
from app.services.compatibility import (
    CompatibilityService,
    _companies_from_profile,
    _fields_from_profile,
    _schools_from_profile,
    _shared_companies,
    _shared_fields,
    _shared_schools,
    _template_starters,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


_NOW = datetime.now(timezone.utc)


def _make_profile(**kwargs) -> ProfileResponse:
    """Return a minimal valid ProfileResponse with overrides."""
    defaults = {
        "user_id": uuid4(),
        "full_name": "Alice Smith",
        "headline": None,
        "bio": None,
        "location": None,
        "company": None,
        "major": None,
        "graduation_year": None,
        "linkedin_url": None,
        "photo_path": None,
        "experiences": None,
        "education": None,
        "profile_one_liner": None,
        "profile_summary": None,
        "summary_provider": None,
        "summary_updated_at": None,
        "created_at": _NOW,
        "updated_at": _NOW,
    }
    defaults.update(kwargs)
    return ProfileResponse(**defaults)


# ---------------------------------------------------------------------------
# _companies_from_profile
# ---------------------------------------------------------------------------


class TestCompaniesFromProfile:
    def test_no_company_no_experiences(self):
        profile = _make_profile()
        assert _companies_from_profile(profile) == set()

    def test_top_level_company_included(self):
        profile = _make_profile(company="Acme Corp")
        assert "acme corp" in _companies_from_profile(profile)

    def test_experience_companies_included(self):
        profile = _make_profile(
            experiences=[{"company": "Beta Inc", "title": "Engineer"}]
        )
        assert "beta inc" in _companies_from_profile(profile)

    def test_company_normalized_to_lowercase(self):
        profile = _make_profile(company="  UPPER CORP  ")
        assert "upper corp" in _companies_from_profile(profile)

    def test_null_experience_company_ignored(self):
        profile = _make_profile(experiences=[{"company": None, "title": "Engineer"}])
        assert _companies_from_profile(profile) == set()


# ---------------------------------------------------------------------------
# _schools_from_profile / _fields_from_profile
# ---------------------------------------------------------------------------


class TestSchoolsAndFieldsFromProfile:
    def test_schools_extracted_from_education(self):
        profile = _make_profile(education=[{"school": "MIT", "degree": "BS"}])
        assert "mit" in _schools_from_profile(profile)

    def test_fields_from_major(self):
        profile = _make_profile(major="Computer Science")
        assert "computer science" in _fields_from_profile(profile)

    def test_fields_from_education_field_of_study(self):
        profile = _make_profile(education=[{"field_of_study": "Electrical Engineering"}])
        assert "electrical engineering" in _fields_from_profile(profile)

    def test_empty_education_returns_empty(self):
        profile = _make_profile(education=[])
        assert _schools_from_profile(profile) == set()
        assert _fields_from_profile(profile) == set()


# ---------------------------------------------------------------------------
# Shared overlap helpers
# ---------------------------------------------------------------------------


class TestSharedHelpers:
    def test_shared_companies_overlap(self):
        a = _make_profile(company="Acme")
        b = _make_profile(company="Acme")
        assert _shared_companies(a, b) == ["Acme"]

    def test_shared_companies_no_overlap(self):
        a = _make_profile(company="Acme")
        b = _make_profile(company="Beta")
        assert _shared_companies(a, b) == []

    def test_shared_schools_overlap(self):
        a = _make_profile(education=[{"school": "MIT"}])
        b = _make_profile(education=[{"school": "MIT"}])
        assert _shared_schools(a, b) == ["Mit"]

    def test_shared_fields_overlap_via_major(self):
        a = _make_profile(major="Electrical Engineering")
        b = _make_profile(major="Electrical Engineering")
        assert _shared_fields(a, b) == ["Electrical Engineering"]


# ---------------------------------------------------------------------------
# CompatibilityService.compute — score
# ---------------------------------------------------------------------------


class TestCompatibilityServiceScore:
    def _service(self):
        return CompatibilityService()

    def test_no_overlap_yields_zero(self):
        viewer = _make_profile(full_name="Alice")
        target = _make_profile(full_name="Bob", company="Beta")
        result = self._service().compute(viewer, target)
        assert result.score == 0.0

    def test_shared_company_adds_thirty_points(self):
        viewer = _make_profile(full_name="Alice", company="Acme")
        target = _make_profile(full_name="Bob", company="Acme")
        result = self._service().compute(viewer, target)
        assert result.score == 30.0
        assert "Acme" in result.shared_companies

    def test_shared_school_adds_twenty_five_points(self):
        viewer = _make_profile(
            full_name="Alice", education=[{"school": "MIT"}]
        )
        target = _make_profile(
            full_name="Bob", education=[{"school": "MIT"}]
        )
        result = self._service().compute(viewer, target)
        assert result.score == 25.0

    def test_same_location_adds_ten_points(self):
        viewer = _make_profile(full_name="Alice", location="Boston, MA")
        target = _make_profile(full_name="Bob", location="Boston, MA")
        result = self._service().compute(viewer, target)
        assert result.score == 10.0

    def test_score_capped_at_100(self):
        """Multiple overlapping signals don't push score past 100."""
        viewer = _make_profile(
            full_name="Alice",
            company="Acme",
            location="Boston, MA",
            education=[{"school": "MIT", "field_of_study": "CS"}],
            experiences=[
                {"company": "Beta"},
                {"company": "Gamma"},
                {"company": "Delta"},
            ],
        )
        target = _make_profile(
            full_name="Bob",
            company="Acme",
            location="Boston, MA",
            education=[{"school": "MIT", "field_of_study": "CS"}],
            experiences=[
                {"company": "Beta"},
                {"company": "Gamma"},
                {"company": "Delta"},
            ],
        )
        result = self._service().compute(viewer, target)
        assert result.score == 100.0


# ---------------------------------------------------------------------------
# CompatibilityService.compute — conversation starters (template fallback)
# ---------------------------------------------------------------------------


class TestCompatibilityServiceStarters:
    def _service(self):
        return CompatibilityService()

    @patch("app.services.compatibility.get_settings")
    def test_falls_back_to_template_when_no_openai_key(self, mock_settings):
        mock_settings.return_value = MagicMock(openai_api_key=None)
        viewer = _make_profile(full_name="Alice", company="Acme")
        target = _make_profile(full_name="Bob", company="Acme")
        result = self._service().compute(viewer, target)
        assert len(result.conversation_starters) >= 1
        assert "Acme" in result.conversation_starters[0]

    @patch("app.services.compatibility.get_settings")
    def test_generic_starter_used_when_no_overlap(self, mock_settings):
        mock_settings.return_value = MagicMock(openai_api_key=None)
        viewer = _make_profile(full_name="Alice")
        target = _make_profile(full_name="Bob")
        result = self._service().compute(viewer, target)
        assert len(result.conversation_starters) >= 1
        assert "Bob" in result.conversation_starters[0]


# ---------------------------------------------------------------------------
# _template_starters
# ---------------------------------------------------------------------------


class TestTemplateStarters:
    def test_company_starter_when_shared_company(self):
        target = _make_profile(full_name="Bob")
        starters = _template_starters(target, ["Acme"], [], [])
        assert any("Acme" in s for s in starters)

    def test_school_starter_when_shared_school(self):
        target = _make_profile(full_name="Bob")
        starters = _template_starters(target, [], ["Mit"], [])
        assert any("Mit" in s for s in starters)

    def test_field_starter_when_shared_field(self):
        target = _make_profile(full_name="Bob")
        starters = _template_starters(target, [], [], ["Computer Science"])
        assert any("Computer Science" in s for s in starters)

    def test_headline_starter_when_no_overlap(self):
        target = _make_profile(full_name="Bob", headline="ML Engineer")
        starters = _template_starters(target, [], [], [])
        assert any("ML Engineer" in s for s in starters)

    def test_generic_starter_when_nothing_available(self):
        target = _make_profile(full_name="Bob")
        starters = _template_starters(target, [], [], [])
        assert any("Bob" in s for s in starters)

    def test_at_most_three_starters_returned(self):
        target = _make_profile(full_name="Bob")
        starters = _template_starters(
            target, ["Acme"], ["Mit"], ["Computer Science"]
        )
        assert len(starters) <= 3
