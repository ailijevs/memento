"""Tests for onboarding helpers and Exa mapping behavior."""

from app.api.profiles import _parse_graduation_year
from app.services.linkedin_enrichment import LinkedInEnrichmentService


def test_parse_graduation_year_parses_yyyy_mm():
    """Should parse the year portion from a YYYY-MM value."""
    assert _parse_graduation_year("2024-05") == 2024


def test_parse_graduation_year_rejects_invalid_value():
    """Invalid or missing values should map to None."""
    assert _parse_graduation_year("unknown") is None
    assert _parse_graduation_year(None) is None


def test_map_exa_payload_extracts_core_fields():
    """Exa payload should map to the normalized profile shape."""
    payload = {
        "results": [
            {
                "url": "https://www.linkedin.com/in/jane-doe/",
                "title": "Jane Doe - Software Engineer",
                "author": "Jane Doe",
                "image": "https://media.example.com/jane.png",
                "summary": "Backend engineer building distributed systems.",
                "text": """Jane Doe\nSoftware Engineer at Acme\nSan Francisco, California, United States\nExperience\nSoftware Engineer at Acme\nEducation\nPurdue University""",
            }
        ]
    }

    mapped = LinkedInEnrichmentService._map_exa_payload(
        payload,
        "https://www.linkedin.com/in/jane-doe/",
    )

    assert mapped["full_name"] == "Jane Doe"
    assert mapped["headline"] == "Software Engineer at Acme"
    assert mapped["location"] == "San Francisco, California, United States"
    assert mapped["profile_image_url"] == "https://media.example.com/jane.png"
    assert mapped["source"] == "exa"
    assert mapped["confidence"] == 0.6
    assert mapped["experiences"]
    assert mapped["education"]
