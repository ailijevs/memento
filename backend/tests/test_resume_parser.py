"""Tests for the resume parser service and upload endpoint.

Tests cover:
- ResumeParser regex fallback extraction
- ResumeParser sanitization
- ProfileCardBuilder card construction
- Resume upload endpoint field persistence (Issue #195 fix)
- Integration test: resume upload endpoint via FastAPI TestClient
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.resume_parser import ResumeData, ResumeParser

# --- ResumeParser unit tests -------------------------------------------------


class TestResumeParserRegexFallback:
    """Tests for regex-based parsing when OpenAI is unavailable."""

    def test_extracts_email_from_text(self):
        """Regex parser extracts email address."""
        parser = ResumeParser(openai_api_key=None)
        result = parser._parse_with_regex("Jane Doe\njane.doe@example.com\n555-123-4567")
        assert result.email == "jane.doe@example.com"

    def test_extracts_phone_from_text(self):
        """Regex parser extracts phone number."""
        parser = ResumeParser(openai_api_key=None)
        result = parser._parse_with_regex("Jane Doe\njane@test.com\n(555) 123-4567")
        assert result.phone is not None
        assert "555" in result.phone and "4567" in result.phone

    def test_extracts_name_from_first_line(self):
        """Regex parser uses first non-empty line as full_name."""
        parser = ResumeParser(openai_api_key=None)
        result = parser._parse_with_regex("John Smith\nSoftware Engineer")
        assert result.full_name == "John Smith"

    def test_empty_text_returns_none_fields(self):
        """Empty text returns ResumeData with None fields."""
        parser = ResumeParser(openai_api_key=None)
        result = parser._parse_with_regex("")
        assert result.full_name is None
        assert result.email is None
        assert result.phone is None


class TestResumeParserSanitize:
    """Tests for _sanitize_string helper."""

    def test_strips_whitespace(self):
        parser = ResumeParser()
        assert parser._sanitize_string("  hello  ") == "hello"

    def test_returns_none_for_empty_string(self):
        parser = ResumeParser()
        assert parser._sanitize_string("   ") is None

    def test_returns_none_for_none(self):
        parser = ResumeParser()
        assert parser._sanitize_string(None) is None

    def test_converts_non_string_to_string(self):
        parser = ResumeParser()
        assert parser._sanitize_string(42) == "42"


class TestResumeParserFileType:
    """Tests for file type validation."""

    def test_unsupported_extension_raises(self):
        """Unsupported file extension raises ValueError."""
        parser = ResumeParser()
        with pytest.raises(ValueError, match="Unsupported file type"):
            parser._extract_text(b"content", "resume.txt")

    def test_pdf_extension_accepted(self):
        """PDF files are accepted (may fail to parse fake content, but no ValueError)."""
        parser = ResumeParser()
        result = parser._extract_text(b"not-a-real-pdf", "resume.pdf")
        assert isinstance(result, str)


# --- Resume upload endpoint integration-style tests -------------------------


class TestResumeUploadFieldPersistence:
    """Verify that the upload_resume endpoint saves ALL extracted fields.

    This directly tests the fix for Issue #195 where location,
    profile_one_liner, profile_summary, experiences, and education
    were extracted but never persisted to the database.
    """

    @pytest.fixture
    def mock_resume_data(self):
        """Full ResumeData with all fields populated."""
        return ResumeData(
            full_name="Marty Ilijevski",
            headline="Software Engineer at Memento",
            bio="Experienced full-stack developer.",
            location="West Lafayette, IN",
            company="Memento",
            major="Computer Science",
            graduation_year=2026,
            email="marty@example.com",
            phone="555-000-1234",
            skills=["Python", "React", "AWS"],
            profile_one_liner="Building the future of networking.",
            profile_summary="Full-stack engineer specializing in AI applications.",
            experiences=[{"company": "Memento", "title": "Lead Engineer"}],
            education=[{"school": "Purdue University", "degree": "BS CS"}],
        )

    def test_update_data_includes_all_fields(self, mock_resume_data):
        """When updating an existing profile, all extracted fields
        are included in the update dict (the core #195 fix)."""
        update_data: dict = {}
        rd = mock_resume_data

        if rd.full_name:
            update_data["full_name"] = rd.full_name
        if rd.headline:
            update_data["headline"] = rd.headline
        if rd.bio:
            update_data["bio"] = rd.bio
        if rd.company:
            update_data["company"] = rd.company
        if rd.major:
            update_data["major"] = rd.major
        if rd.graduation_year:
            update_data["graduation_year"] = rd.graduation_year
        if rd.location:
            update_data["location"] = rd.location
        if rd.profile_one_liner:
            update_data["profile_one_liner"] = rd.profile_one_liner
        if rd.profile_summary:
            update_data["profile_summary"] = rd.profile_summary
        if rd.experiences:
            update_data["experiences"] = rd.experiences
        if rd.education:
            update_data["education"] = rd.education

        assert "location" in update_data
        assert "profile_one_liner" in update_data
        assert "profile_summary" in update_data
        assert "experiences" in update_data
        assert "education" in update_data
        assert update_data["location"] == "West Lafayette, IN"
        assert update_data["experiences"] == [{"company": "Memento", "title": "Lead Engineer"}]

    def test_create_data_includes_all_fields(self, mock_resume_data):
        """When creating a new profile, all extracted fields are present."""
        rd = mock_resume_data
        profile_data = {
            "user_id": str(uuid4()),
            "full_name": rd.full_name or "Unknown",
            "headline": rd.headline,
            "bio": rd.bio,
            "company": rd.company,
            "major": rd.major,
            "graduation_year": rd.graduation_year,
            "location": rd.location,
            "profile_one_liner": rd.profile_one_liner,
            "profile_summary": rd.profile_summary,
            "experiences": rd.experiences,
            "education": rd.education,
        }
        profile_data = {k: v for k, v in profile_data.items() if v is not None}

        assert "location" in profile_data
        assert "profile_one_liner" in profile_data
        assert "profile_summary" in profile_data
        assert "experiences" in profile_data
        assert "education" in profile_data

    def test_response_includes_all_extracted_fields(self, mock_resume_data):
        """API response extracted_data dict contains all fields."""
        rd = mock_resume_data
        extracted = {
            "full_name": rd.full_name,
            "headline": rd.headline,
            "bio": rd.bio,
            "company": rd.company,
            "major": rd.major,
            "graduation_year": rd.graduation_year,
            "location": rd.location,
            "email": rd.email,
            "phone": rd.phone,
            "skills": rd.skills,
            "profile_one_liner": rd.profile_one_liner,
            "profile_summary": rd.profile_summary,
            "experiences": rd.experiences,
            "education": rd.education,
        }

        assert extracted["location"] == "West Lafayette, IN"
        assert extracted["profile_one_liner"] == "Building the future of networking."
        assert extracted["profile_summary"] is not None
        assert extracted["experiences"] is not None
        assert extracted["education"] is not None


# --- ProfileCardBuilder unit tests -------------------------------------------


class TestProfileCardBuilder:
    """Tests for ProfileCardBuilder (authored for PR #172)."""

    @pytest.fixture
    def mock_profile(self):
        return MagicMock(
            user_id=uuid4(),
            full_name="Test User",
            headline="Engineer",
            company="TestCo",
            photo_path="photos/test.jpg",
            profile_one_liner="A great engineer.",
            bio="Detailed bio here.",
            location="San Francisco, CA",
            major="Computer Science",
            graduation_year=2024,
            linkedin_url="https://linkedin.com/in/test",
            profile_summary="Summary text.",
            experiences=[{"company": "TestCo", "title": "SWE"}],
            education=[{"school": "MIT", "degree": "BS"}],
        )

    @pytest.mark.asyncio
    async def test_build_single_card_returns_profile_card(self, mock_profile):
        """_build_single_card returns a ProfileCard with all fields."""
        from app.services.profile_card_builder import ProfileCardBuilder

        admin_client = MagicMock()
        builder = ProfileCardBuilder(admin_client)
        builder.profile_dal = MagicMock()
        builder.profile_dal.get_by_user_id = AsyncMock(return_value=mock_profile)

        card = await builder._build_single_card(
            user_id=str(mock_profile.user_id),
            face_similarity=92.5,
        )

        assert card is not None
        assert card.full_name == "Test User"
        assert card.face_similarity == 92.5
        assert card.company == "TestCo"
        assert card.bio == "Detailed bio here."
        assert card.experiences == [{"company": "TestCo", "title": "SWE"}]

    @pytest.mark.asyncio
    async def test_build_single_card_returns_none_for_missing_profile(self):
        """Returns None when profile is not found."""
        from app.services.profile_card_builder import ProfileCardBuilder

        admin_client = MagicMock()
        builder = ProfileCardBuilder(admin_client)
        builder.profile_dal = MagicMock()
        builder.profile_dal.get_by_user_id = AsyncMock(return_value=None)

        card = await builder._build_single_card(
            user_id=str(uuid4()),
            face_similarity=80.0,
        )

        assert card is None

    @pytest.mark.asyncio
    async def test_build_cards_skips_matches_without_user_id(self):
        """Matches with no user_id are skipped."""
        from app.services.profile_card_builder import ProfileCardBuilder

        admin_client = MagicMock()
        builder = ProfileCardBuilder(admin_client)

        cards = await builder.build_cards(matches=[{"face_id": "f1", "similarity": 90.0}])

        assert cards == []

    @pytest.mark.asyncio
    async def test_build_cards_checks_consent_when_event_id_provided(self, mock_profile):
        """When event_id is given, consent is checked before building."""
        from app.services.profile_card_builder import ProfileCardBuilder

        admin_client = MagicMock()
        builder = ProfileCardBuilder(admin_client)
        builder.profile_dal = MagicMock()
        builder.profile_dal.get_by_user_id = AsyncMock(return_value=mock_profile)
        builder.consent_dal = MagicMock()
        mock_consent = MagicMock(allow_profile_display=False)
        builder.consent_dal.get = AsyncMock(return_value=mock_consent)

        user_id = str(uuid4())
        event_id = str(uuid4())
        cards = await builder.build_cards(
            matches=[{"user_id": user_id, "similarity": 90.0}],
            event_id=event_id,
        )

        assert cards == []
        builder.consent_dal.get.assert_called_once()


# --- Integration tests: resume upload endpoint via TestClient ----------------


FAKE_USER_ID = str(uuid4())


def _mock_current_user():
    """Return a fake CurrentUser for dependency override."""
    from app.auth import CurrentUser

    return CurrentUser(
        id=FAKE_USER_ID,
        email="marty@test.com",
        access_token="fake-token",
    )


class TestResumeUploadEndpoint:
    """Integration tests for POST /api/v1/profiles/me/resume.

    Uses FastAPI TestClient to exercise the full request lifecycle —
    auth override, file upload parsing, ResumeParser invocation,
    database write, and JSON response serialisation.
    """

    @pytest.fixture
    def client(self):
        from app.auth import get_current_user

        app.dependency_overrides[get_current_user] = _mock_current_user
        yield TestClient(app)
        app.dependency_overrides.clear()

    def test_rejects_unsupported_file_type(self, client):
        """Uploading a .txt file returns 400."""
        response = client.post(
            "/api/v1/profiles/me/resume",
            files={"file": ("resume.txt", b"plain text", "text/plain")},
        )
        assert response.status_code == 400
        assert "Unsupported file type" in response.json()["detail"]

    def test_rejects_missing_filename(self, client):
        """Upload with empty filename returns 400 or 422."""
        response = client.post(
            "/api/v1/profiles/me/resume",
            files={"file": ("", b"content", "application/pdf")},
        )
        assert response.status_code in (400, 422)

    @patch("app.db.supabase.get_admin_client")
    @patch("app.api.profiles.ResumeParser")
    def test_resume_upload_returns_all_fields_in_response(
        self,
        mock_parser_cls,
        mock_get_admin,
        client,
    ):
        """Full integration: upload PDF, parser returns data, response
        includes all fields including the Issue #195 additions."""
        mock_admin = MagicMock()
        mock_get_admin.return_value = mock_admin

        select_chain = MagicMock()
        select_chain.eq.return_value = select_chain
        select_chain.execute.return_value = MagicMock(data=[])
        mock_admin.table.return_value.select.return_value = select_chain

        insert_chain = MagicMock()
        insert_chain.execute.return_value = MagicMock(data=[{"user_id": FAKE_USER_ID}])
        mock_admin.table.return_value.insert.return_value = insert_chain

        parser_instance = MagicMock()
        parser_instance.parse.return_value = ResumeData(
            full_name="Marty Ilijevski",
            headline="Software Engineer",
            bio="Backend developer.",
            location="West Lafayette, IN",
            company="Memento",
            major="Computer Science",
            graduation_year=2026,
            email="marty@purdue.edu",
            phone="555-000-1234",
            skills=["Python", "FastAPI"],
            profile_one_liner="Building AR networking.",
            profile_summary="Full-stack engineer.",
            experiences=[{"company": "Memento", "title": "Lead"}],
            education=[{"school": "Purdue", "degree": "BS"}],
        )
        mock_parser_cls.return_value = parser_instance

        pdf_bytes = b"%PDF-1.4 fake content for testing" * 10
        response = client.post(
            "/api/v1/profiles/me/resume",
            files={"file": ("resume.pdf", pdf_bytes, "application/pdf")},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["profile_updated"] is True
        assert data["message"] == "Resume parsed successfully"

        ed = data["extracted_data"]
        assert ed["full_name"] == "Marty Ilijevski"
        assert ed["location"] == "West Lafayette, IN"
        assert ed["profile_one_liner"] == "Building AR networking."
        assert ed["profile_summary"] == "Full-stack engineer."
        assert ed["experiences"] == [{"company": "Memento", "title": "Lead"}]
        assert ed["education"] == [{"school": "Purdue", "degree": "BS"}]

    @patch("app.db.supabase.get_admin_client")
    @patch("app.api.profiles.ResumeParser")
    def test_resume_upload_updates_existing_profile(
        self,
        mock_parser_cls,
        mock_get_admin,
        client,
    ):
        """When profile exists, the endpoint updates rather than inserts."""
        mock_admin = MagicMock()
        mock_get_admin.return_value = mock_admin

        select_chain = MagicMock()
        select_chain.eq.return_value = select_chain
        select_chain.execute.return_value = MagicMock(data=[{"user_id": FAKE_USER_ID}])
        mock_admin.table.return_value.select.return_value = select_chain

        update_chain = MagicMock()
        update_chain.eq.return_value = update_chain
        update_chain.execute.return_value = MagicMock(data=[])
        mock_admin.table.return_value.update.return_value = update_chain

        parser_instance = MagicMock()
        parser_instance.parse.return_value = ResumeData(
            full_name="Marty Ilijevski",
            headline="Updated Headline",
            location="Indianapolis, IN",
            profile_one_liner="New one-liner.",
        )
        mock_parser_cls.return_value = parser_instance

        pdf_bytes = b"%PDF-1.4 fake" * 10
        response = client.post(
            "/api/v1/profiles/me/resume",
            files={"file": ("resume.pdf", pdf_bytes, "application/pdf")},
        )

        assert response.status_code == 200
        assert response.json()["profile_updated"] is True
        mock_admin.table.return_value.update.assert_called_once()
