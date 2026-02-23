"""LinkedIn URL enrichment service with pluggable provider adapters."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

import httpx

from app.config import get_settings

PDL_API_BASE = "https://api.peopledatalabs.com/v5"
EXA_API_BASE = "https://api.exa.ai"


class LinkedInEnrichmentError(Exception):
    """Raised when enrichment fails."""

    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class LinkedInEnrichmentService:
    """Enrich profile fields from a LinkedIn URL via upstream providers."""

    @staticmethod
    def normalize_linkedin_url(linkedin_url: str) -> str:
        """Normalize and validate a LinkedIn profile URL."""
        normalized = linkedin_url.strip()

        if normalized.startswith("www."):
            normalized = f"https://{normalized}"
        elif not normalized.startswith(("https://", "http://")):
            normalized = f"https://{normalized}"

        normalized = normalized.replace("http://", "https://")

        parsed = urlparse(normalized)
        host = (parsed.netloc or "").lower()
        if host.startswith("www."):
            host = host[4:]

        if host != "linkedin.com" or not parsed.path.startswith("/in/"):
            raise LinkedInEnrichmentError(
                "Only LinkedIn person profile URLs are supported (linkedin.com/in/...).",
                status_code=400,
            )

        return normalized.split("?")[0].rstrip("/") + "/"

    async def enrich_profile(self, linkedin_url: str, provider: str = "pdl") -> dict[str, Any]:
        """Enrich profile data for a LinkedIn URL."""
        normalized_url = self.normalize_linkedin_url(linkedin_url)

        provider_normalized = provider.lower().strip()
        if provider_normalized == "auto":
            try:
                return await self._enrich_with_pdl(normalized_url)
            except LinkedInEnrichmentError:
                return await self._enrich_with_exa(normalized_url)
        if provider_normalized == "pdl":
            return await self._enrich_with_pdl(normalized_url)
        if provider_normalized == "exa":
            return await self._enrich_with_exa(normalized_url)
        if provider_normalized not in {"auto", "pdl", "exa"}:
            raise LinkedInEnrichmentError(
                f"Unsupported provider '{provider}'. Supported providers: auto, pdl, exa",
                status_code=400,
            )

        raise LinkedInEnrichmentError("Unsupported provider.", status_code=400)

    async def _enrich_with_pdl(self, linkedin_url: str) -> dict[str, Any]:
        """Use People Data Labs Person Enrichment with LinkedIn URL input."""
        settings = get_settings()
        if not settings.pdl_api_key:
            raise LinkedInEnrichmentError(
                (
                    "PDL API key missing. Set PDL_API_KEY in backend/.env "
                    "before calling this endpoint."
                ),
                status_code=503,
            )

        # PDL supports enriching a person by profile URL.
        params = {
            "profile": linkedin_url,
            "pretty": "false",
            "min_likelihood": "2",
        }
        headers = {"X-Api-Key": settings.pdl_api_key}

        async with httpx.AsyncClient(timeout=25.0) as client:
            response = await client.get(
                f"{PDL_API_BASE}/person/enrich", params=params, headers=headers
            )

        if response.status_code == 200:
            payload = response.json()
            return self._map_pdl_payload(payload, linkedin_url)

        if response.status_code in (401, 403):
            raise LinkedInEnrichmentError(
                "PDL authentication failed. Verify PDL_API_KEY.",
                status_code=502,
            )

        if response.status_code == 404:
            raise LinkedInEnrichmentError(
                "No enrichment result found for this LinkedIn URL.",
                status_code=404,
            )

        detail = response.text[:300]
        raise LinkedInEnrichmentError(
            f"PDL request failed with status {response.status_code}: {detail}",
            status_code=502,
        )

    async def _enrich_with_exa(self, linkedin_url: str) -> dict[str, Any]:
        """Use Exa contents API to extract profile data from page content."""
        settings = get_settings()
        if not settings.exa_api_key:
            raise LinkedInEnrichmentError(
                (
                    "Exa API key missing. Set EXA_API_KEY in backend/.env "
                    "before calling this endpoint."
                ),
                status_code=503,
            )

        headers = {
            "x-api-key": settings.exa_api_key,
            "content-type": "application/json",
        }
        payload = {
            "urls": [linkedin_url],
            "text": True,
            "summary": True,
            "livecrawl": "fallback",
        }

        async with httpx.AsyncClient(timeout=25.0) as client:
            response = await client.post(f"{EXA_API_BASE}/contents", headers=headers, json=payload)

        if response.status_code in (401, 403):
            raise LinkedInEnrichmentError(
                "Exa authentication failed. Verify EXA_API_KEY.",
                status_code=502,
            )
        if response.status_code >= 400:
            detail = response.text[:300]
            raise LinkedInEnrichmentError(
                f"Exa request failed with status {response.status_code}: {detail}",
                status_code=502,
            )

        body = response.json()
        results = body.get("results", [])
        if not results:
            raise LinkedInEnrichmentError(
                "No enrichment result found for this LinkedIn URL.", status_code=404
            )

        return self._map_exa_payload(body, linkedin_url)

    @staticmethod
    def _map_pdl_payload(payload: dict[str, Any], linkedin_url: str) -> dict[str, Any]:
        """Map People Data Labs payload into a stable internal enrichment shape."""
        profile_data = payload.get("data") if isinstance(payload.get("data"), dict) else payload

        location = profile_data.get("location_name")
        if not isinstance(location, str) or not location.strip():
            locality = profile_data.get("locality")
            region = profile_data.get("region")
            country = profile_data.get("country")
            location = (
                ", ".join(
                    [
                        part
                        for part in [locality, region, country]
                        if isinstance(part, str) and part.strip()
                    ]
                )
                or None
            )

        experiences: list[dict[str, Any]] = []
        for item in profile_data.get("experience", []) or []:
            if not isinstance(item, dict):
                continue
            title = LinkedInEnrichmentService._as_text(item.get("title"), keys=["name"])
            company = LinkedInEnrichmentService._as_text(
                item.get("company"),
                keys=["name", "display_name"],
            ) or LinkedInEnrichmentService._as_text(item.get("company_name"))
            experiences.append(
                {
                    "title": title or LinkedInEnrichmentService._as_text(item.get("job_title")),
                    "company": company or LinkedInEnrichmentService._as_text(item.get("name")),
                    "start_date": item.get("start_date"),
                    "end_date": item.get("end_date"),
                    "description": LinkedInEnrichmentService._as_text(item.get("summary"))
                    or LinkedInEnrichmentService._as_text(item.get("description")),
                }
            )

        education: list[dict[str, Any]] = []
        for item in profile_data.get("education", []) or []:
            if not isinstance(item, dict):
                continue

            degrees = item.get("degrees")
            degree = degrees[0] if isinstance(degrees, list) and degrees else item.get("degree")
            majors = item.get("majors")
            field_of_study = majors[0] if isinstance(majors, list) and majors else item.get("major")
            school = (
                LinkedInEnrichmentService._as_text(item.get("school"), keys=["name"])
                or LinkedInEnrichmentService._as_text(item.get("school_name"))
                or LinkedInEnrichmentService._as_text(item.get("name"))
            )

            education.append(
                {
                    "school": school,
                    "degree": LinkedInEnrichmentService._as_text(degree, keys=["name"]),
                    "field_of_study": LinkedInEnrichmentService._as_text(
                        field_of_study, keys=["name"]
                    ),
                    "start_date": item.get("start_date"),
                    "end_date": item.get("end_date"),
                }
            )

        profile_image_url = (
            profile_data.get("profile_pic_url")
            or profile_data.get("linkedin_profile_photo_url")
            or profile_data.get("image_url")
            or profile_data.get("photo_url")
        )

        return {
            "full_name": LinkedInEnrichmentService._as_text(profile_data.get("full_name"))
            or LinkedInEnrichmentService._as_text(profile_data.get("name")),
            "bio": LinkedInEnrichmentService._as_text(profile_data.get("summary"))
            or LinkedInEnrichmentService._as_text(profile_data.get("bio")),
            "headline": LinkedInEnrichmentService._as_text(
                profile_data.get("job_title"), keys=["name"]
            )
            or LinkedInEnrichmentService._as_text(profile_data.get("headline")),
            "location": location,
            "experiences": experiences,
            "education": education,
            "profile_image_url": profile_image_url,
            "linkedin_url": profile_data.get("linkedin_url") or linkedin_url,
            "source": "pdl",
            "confidence": payload.get("likelihood"),
            "raw_payload": payload,
        }

    @staticmethod
    def _as_text(value: Any, keys: list[str] | None = None) -> str | None:
        """Extract a representative string from primitive/list/dict values."""
        if value is None:
            return None
        if isinstance(value, str):
            stripped = value.strip()
            return stripped if stripped else None
        if isinstance(value, (int, float, bool)):
            return str(value)
        if isinstance(value, list):
            for item in value:
                text = LinkedInEnrichmentService._as_text(item, keys=keys)
                if text:
                    return text
            return None
        if isinstance(value, dict):
            for key in keys or ["name", "title", "value"]:
                if key in value:
                    text = LinkedInEnrichmentService._as_text(value.get(key), keys=keys)
                    if text:
                        return text
            return None
        return None

    @staticmethod
    def _map_exa_payload(payload: dict[str, Any], linkedin_url: str) -> dict[str, Any]:
        """Map Exa contents payload into the internal enrichment shape."""
        results = payload.get("results", [])
        if not results:
            raise LinkedInEnrichmentError("No Exa results available.", status_code=404)

        row = results[0]
        text = row.get("text") or ""
        summary = row.get("summary")

        name = row.get("author") or LinkedInEnrichmentService._extract_name_from_title(
            row.get("title")
        )
        headline = LinkedInEnrichmentService._extract_headline(text)
        location = LinkedInEnrichmentService._extract_location(text)

        return {
            "full_name": name,
            "bio": summary or LinkedInEnrichmentService._extract_bio(text),
            "headline": headline,
            "location": location,
            "experiences": LinkedInEnrichmentService._extract_experiences(text),
            "education": LinkedInEnrichmentService._extract_education(text),
            "profile_image_url": row.get("image"),
            "linkedin_url": row.get("url") or linkedin_url,
            "source": "exa",
            "confidence": 0.6,
            "raw_payload": payload,
        }

    @staticmethod
    def _extract_name_from_title(title: str | None) -> str | None:
        if not title:
            return None
        return title.split(" - ")[0].strip()

    @staticmethod
    def _extract_bio(text: str) -> str | None:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        for line in lines:
            if (
                len(line) > 40
                and "experience" not in line.lower()
                and "education" not in line.lower()
            ):
                return line
        return None

    @staticmethod
    def _extract_headline(text: str) -> str | None:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        for idx, line in enumerate(lines[:8]):
            lower = line.lower()
            if " at " in lower or "student" in lower or "engineer" in lower:
                return line
            if idx == 1 and len(line) > 8:
                return line
        return None

    @staticmethod
    def _extract_location(text: str) -> str | None:
        location_match = re.search(
            r"([A-Z][A-Za-z .'-]+,\s*[A-Z][A-Za-z .'-]+(?:,\s*[A-Z][A-Za-z .'-]+)?)",
            text,
        )
        return location_match.group(1).strip() if location_match else None

    @staticmethod
    def _extract_experiences(text: str) -> list[dict[str, Any]]:
        experiences: list[dict[str, Any]] = []
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        for line in lines:
            if " at " in line and len(experiences) < 10:
                parts = re.split(r"\s+at\s+", line, maxsplit=1, flags=re.IGNORECASE)
                if len(parts) == 2:
                    experiences.append(
                        {
                            "title": parts[0].strip(),
                            "company": parts[1].strip(),
                            "start_date": None,
                            "end_date": None,
                            "description": None,
                        }
                    )
        return experiences

    @staticmethod
    def _extract_education(text: str) -> list[dict[str, Any]]:
        education: list[dict[str, Any]] = []
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        for line in lines:
            if (
                any(token in line for token in ["University", "College", "Institute"])
                and len(education) < 5
            ):
                education.append(
                    {
                        "school": line,
                        "degree": None,
                        "field_of_study": None,
                        "start_date": None,
                        "end_date": None,
                    }
                )
        return education
