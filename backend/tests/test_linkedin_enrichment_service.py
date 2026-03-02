"""Tests for LinkedIn enrichment service mapping/validation."""

import pytest

from app.services.linkedin_enrichment import (
    LinkedInEnrichmentError,
    LinkedInEnrichmentService,
)


def test_normalize_linkedin_url_accepts_profile_url():
    """Normalization should enforce https + canonical slash."""
    url = "www.linkedin.com/in/jane-doe?trk=foo"
    normalized = LinkedInEnrichmentService.normalize_linkedin_url(url)
    assert normalized == "https://www.linkedin.com/in/jane-doe/"


def test_normalize_linkedin_url_rejects_non_profile_urls():
    """Only LinkedIn person profile URLs should be accepted."""
    with pytest.raises(LinkedInEnrichmentError):
        LinkedInEnrichmentService.normalize_linkedin_url("https://linkedin.com/company/openai")


def test_map_pdl_payload_builds_normalized_shape():
    """PDL payload should map to the internal response schema."""
    payload = {
        "likelihood": 9,
        "data": {
            "full_name": "Jane Doe",
            "job_title": "Software Engineer",
            "summary": "Builder of backend systems.",
            "location_name": "San Francisco, California, United States",
            "linkedin_url": "https://www.linkedin.com/in/jane-doe/",
            "linkedin_profile_photo_url": "https://cdn.example.com/jane.jpg",
            "experience": [
                {
                    "title": "Software Engineer",
                    "company_name": "Acme Inc",
                    "start_date": "2023-01",
                    "end_date": None,
                    "description": "Built APIs",
                }
            ],
            "education": [
                {
                    "school_name": "Purdue University",
                    "degrees": ["BS"],
                    "majors": ["Computer Engineering"],
                    "start_date": "2019-08",
                    "end_date": "2023-05",
                }
            ],
        },
    }

    mapped = LinkedInEnrichmentService._map_pdl_payload(
        payload,
        "https://www.linkedin.com/in/jane-doe/",
    )

    assert mapped["full_name"] == "Jane Doe"
    assert mapped["headline"] == "Software Engineer"
    assert mapped["bio"] == "Builder of backend systems."
    assert mapped["location"] == "San Francisco, California, United States"
    assert mapped["profile_image_url"] == "https://cdn.example.com/jane.jpg"
    assert mapped["source"] == "pdl"
    assert mapped["confidence"] == 9
    assert len(mapped["experiences"]) == 1
    assert mapped["experiences"][0]["company"] == "Acme Inc"
    assert len(mapped["education"]) == 1
    assert mapped["education"][0]["school"] == "Purdue University"
