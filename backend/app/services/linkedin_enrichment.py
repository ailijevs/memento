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
        raw_data = payload.get("data")
        profile_data: dict[str, Any] = raw_data if isinstance(raw_data, dict) else payload
        print(f"[PDL-DEBUG] profile_data keys: {list(profile_data.keys())}")
        raw_exp_key = "experience" if "experience" in profile_data else "experiences"
        raw_exp_data = profile_data.get(raw_exp_key, []) or []
        print(f"[PDL-DEBUG] experience key={raw_exp_key!r}, count={len(raw_exp_data)}")
        if raw_exp_data and isinstance(raw_exp_data[0], dict):
            print(f"[PDL-DEBUG] first exp keys: {list(raw_exp_data[0].keys())}")

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
        raw_exp = profile_data.get("experience") or profile_data.get("experiences") or []
        for item in raw_exp:
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
        raw_edu = profile_data.get("education") or profile_data.get("educations") or []
        for item in raw_edu:
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
    def _strip_markdown(text: str) -> str:
        """Remove common markdown formatting from Exa-scraped LinkedIn text."""
        cleaned = re.sub(r"#{1,6}\s*", "", text)
        cleaned = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", cleaned)
        cleaned = re.sub(r"\*{1,2}([^*]+)\*{1,2}", r"\1", cleaned)
        cleaned = re.sub(r"__([^_]+)__", r"\1", cleaned)
        cleaned = re.sub(r"`([^`]+)`", r"\1", cleaned)
        cleaned = re.sub(r"^[>\-*]\s+", "", cleaned, flags=re.MULTILINE)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        return cleaned.strip()

    @staticmethod
    def _map_exa_payload(payload: dict[str, Any], linkedin_url: str) -> dict[str, Any]:
        """Map Exa contents payload into the internal enrichment shape."""
        results = payload.get("results", [])
        if not results:
            raise LinkedInEnrichmentError("No Exa results available.", status_code=404)

        row = results[0]
        raw_text = row.get("text") or ""
        text = LinkedInEnrichmentService._strip_markdown(raw_text)
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
        noise_patterns = [
            "follower",
            "connection",
            "experience",
            "education",
            "see all",
            "show all",
            "people also viewed",
            "more activity",
            "join now",
            "sign in",
            "agree & join",
            "mutual connection",
            "report this profile",
        ]
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        for line in lines:
            lower = line.lower()
            if len(line) > 40 and not any(p in lower for p in noise_patterns):
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

        in_experience_section = False
        i = 0
        while i < len(lines) and len(experiences) < 10:
            lower = lines[i].lower()

            if lower in ("experience", "work experience"):
                in_experience_section = True
                i += 1
                continue

            if in_experience_section and lower in (
                "education",
                "licenses & certifications",
                "skills",
                "volunteer experience",
                "publications",
                "projects",
                "honors & awards",
            ):
                break

            non_title_words = {"student", "studying", "attended", "alumni", "member"}
            if " at " in lines[i] and not lower.startswith(("http", "see ")):
                parts = re.split(r"\s+at\s+", lines[i], maxsplit=1, flags=re.IGNORECASE)
                title_lower = parts[0].strip().lower() if len(parts) == 2 else ""
                if (
                    len(parts) == 2
                    and len(parts[0]) < 100
                    and len(parts[1]) < 100
                    and title_lower not in non_title_words
                ):
                    dates = LinkedInEnrichmentService._extract_date_range(
                        lines[i + 1] if i + 1 < len(lines) else ""
                    )
                    experiences.append(
                        {
                            "title": parts[0].strip(),
                            "company": parts[1].strip(),
                            "start_date": dates[0],
                            "end_date": dates[1],
                            "description": None,
                        }
                    )

            elif in_experience_section and len(lines[i]) < 80:
                if i + 1 < len(lines) and len(lines[i + 1]) < 80:
                    title_candidate = lines[i]
                    company_candidate = lines[i + 1]
                    if not any(
                        p in title_candidate.lower()
                        for p in ("follower", "connection", "http", "see ")
                    ):
                        dates = LinkedInEnrichmentService._extract_date_range(
                            lines[i + 2] if i + 2 < len(lines) else ""
                        )
                        experiences.append(
                            {
                                "title": title_candidate,
                                "company": company_candidate,
                                "start_date": dates[0],
                                "end_date": dates[1],
                                "description": None,
                            }
                        )
                        i += 2

            i += 1

        return experiences

    @staticmethod
    def _extract_education(text: str) -> list[dict[str, Any]]:
        education: list[dict[str, Any]] = []
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        school_tokens = ("University", "College", "Institute", "School", "Academy", "Polytechnic")

        in_education_section = False
        i = 0
        while i < len(lines) and len(education) < 5:
            lower = lines[i].lower()

            if lower == "education":
                in_education_section = True
                i += 1
                continue

            if in_education_section and lower in (
                "licenses & certifications",
                "skills",
                "volunteer experience",
                "publications",
                "projects",
                "honors & awards",
                "recommendations",
            ):
                break

            is_school_line = any(token in lines[i] for token in school_tokens)

            if is_school_line and len(lines[i]) < 120:
                school_text = lines[i]
                at_match = re.match(r".+?\s+at\s+(.+)", school_text, re.IGNORECASE)
                school = at_match.group(1).strip() if at_match else school_text
                degree = None
                field_of_study = None
                dates: tuple[str | None, str | None] = (None, None)

                if i + 1 < len(lines):
                    next_line = lines[i + 1]
                    next_lower = next_line.lower()
                    if any(
                        d in next_lower
                        for d in (
                            "bachelor",
                            "master",
                            "associate",
                            "doctor",
                            "b.s.",
                            "b.a.",
                            "m.s.",
                            "m.a.",
                            "ph.d",
                            "mba",
                            "bs,",
                            "ba,",
                            "ms,",
                        )
                    ):
                        degree_parts = next_line.split(",", 1)
                        degree = degree_parts[0].strip()
                        if len(degree_parts) > 1:
                            field_of_study = degree_parts[1].strip()
                        i += 1

                if i + 1 < len(lines):
                    dates = LinkedInEnrichmentService._extract_date_range(lines[i + 1])
                    if dates[0]:
                        i += 1

                education.append(
                    {
                        "school": school,
                        "degree": degree,
                        "field_of_study": field_of_study,
                        "start_date": dates[0],
                        "end_date": dates[1],
                    }
                )

            i += 1

        return education

    @staticmethod
    def _extract_date_range(line: str) -> tuple[str | None, str | None]:
        """Try to pull a date range like 'Jan 2020 - Present' from a line."""
        date_pattern = r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\.?\s+\d{4}|\d{4})"
        present_pattern = r"(Present|Current|Now)"
        match = re.search(
            rf"{date_pattern}\s*[-–—]\s*(?:{date_pattern}|{present_pattern})",
            line,
            re.IGNORECASE,
        )
        if match:
            start = match.group(1)
            end = match.group(2) or match.group(3)
            return (
                start,
                end if end and end.lower() not in ("present", "current", "now") else None,
            )
        single = re.search(date_pattern, line, re.IGNORECASE)
        if single:
            return (single.group(1), None)
        return (None, None)
