"""Compute compatibility scores and generate conversation starters between two profiles."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

from app.config import get_settings
from app.schemas import ProfileResponse

logger = logging.getLogger(__name__)


@dataclass
class CompatibilityResult:
    score: float  # 0–100
    shared_companies: list[str] = field(default_factory=list)
    shared_schools: list[str] = field(default_factory=list)
    shared_fields: list[str] = field(default_factory=list)
    conversation_starters: list[str] = field(default_factory=list)


class CompatibilityService:
    """Score two profiles and suggest ice-breaker conversation starters."""

    def compute(self, viewer: ProfileResponse, target: ProfileResponse) -> CompatibilityResult:
        shared_companies = _shared_companies(viewer, target)
        shared_schools = _shared_schools(viewer, target)
        shared_fields = _shared_fields(viewer, target)
        same_location = bool(
            viewer.location and target.location and viewer.location.strip().lower() == target.location.strip().lower()
        )

        score = min(
            100.0,
            len(shared_companies) * 30.0
            + len(shared_schools) * 25.0
            + len(shared_fields) * 20.0
            + (10.0 if same_location else 0.0),
        )

        starters = self._generate_starters(viewer, target, shared_companies, shared_schools, shared_fields)

        return CompatibilityResult(
            score=round(score, 1),
            shared_companies=shared_companies,
            shared_schools=shared_schools,
            shared_fields=shared_fields,
            conversation_starters=starters,
        )

    def _generate_starters(
        self,
        viewer: ProfileResponse,
        target: ProfileResponse,
        shared_companies: list[str],
        shared_schools: list[str],
        shared_fields: list[str],
    ) -> list[str]:
        settings = get_settings()
        if settings.openai_api_key:
            try:
                return self._generate_with_openai(
                    settings.openai_api_key,
                    viewer,
                    target,
                    shared_companies,
                    shared_schools,
                    shared_fields,
                )
            except Exception as exc:
                logger.warning("OpenAI conversation starter generation failed: %s", exc)

        return _template_starters(target, shared_companies, shared_schools, shared_fields)

    def _generate_with_openai(
        self,
        api_key: str,
        viewer: ProfileResponse,
        target: ProfileResponse,
        shared_companies: list[str],
        shared_schools: list[str],
        shared_fields: list[str],
    ) -> list[str]:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)

        context_parts = [
            f"You just met {target.full_name} ({target.headline or 'no headline'}, {target.company or 'no company'}).",
            f"Your name is {viewer.full_name}.",
        ]
        if shared_companies:
            context_parts.append(f"You've both worked at: {', '.join(shared_companies)}.")
        if shared_schools:
            context_parts.append(f"You both attended: {', '.join(shared_schools)}.")
        if shared_fields:
            context_parts.append(f"You share fields of study: {', '.join(shared_fields)}.")
        if target.bio:
            context_parts.append(f"Their bio: {target.bio[:300]}")
        if target.location:
            context_parts.append(f"They're based in {target.location}.")

        prompt = (
            " ".join(context_parts)
            + "\n\nWrite exactly 3 short, natural, first-person conversation starters to use when meeting them."
            " Return a JSON array of strings, no keys, no explanation."
        )

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.8,
        )

        raw = (response.choices[0].message.content or "").strip()
        starters = json.loads(raw)
        if isinstance(starters, list):
            return [str(s).strip() for s in starters[:3] if s]
        raise ValueError("Unexpected response shape from OpenAI")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _companies_from_profile(profile: ProfileResponse) -> set[str]:
    companies: set[str] = set()
    if profile.company:
        companies.add(profile.company.strip().lower())
    for exp in profile.experiences or []:
        c = str(exp.get("company") or "").strip().lower()
        if c:
            companies.add(c)
    return companies


def _schools_from_profile(profile: ProfileResponse) -> set[str]:
    schools: set[str] = set()
    for edu in profile.education or []:
        s = str(edu.get("school") or "").strip().lower()
        if s:
            schools.add(s)
    return schools


def _fields_from_profile(profile: ProfileResponse) -> set[str]:
    fields: set[str] = set()
    if profile.major:
        fields.add(profile.major.strip().lower())
    for edu in profile.education or []:
        f = str(edu.get("field_of_study") or "").strip().lower()
        if f:
            fields.add(f)
    return fields


def _shared_companies(a: ProfileResponse, b: ProfileResponse) -> list[str]:
    overlap = _companies_from_profile(a) & _companies_from_profile(b)
    return sorted(c.title() for c in overlap)


def _shared_schools(a: ProfileResponse, b: ProfileResponse) -> list[str]:
    overlap = _schools_from_profile(a) & _schools_from_profile(b)
    return sorted(s.title() for s in overlap)


def _shared_fields(a: ProfileResponse, b: ProfileResponse) -> list[str]:
    overlap = _fields_from_profile(a) & _fields_from_profile(b)
    return sorted(f.title() for f in overlap)


def _template_starters(
    target: ProfileResponse,
    shared_companies: list[str],
    shared_schools: list[str],
    shared_fields: list[str],
) -> list[str]:
    starters: list[str] = []

    if shared_companies:
        starters.append(f"I see we've both worked at {shared_companies[0]} — what was your experience like there?")
    if shared_schools:
        starters.append(f"Did you enjoy your time at {shared_schools[0]}?")
    if shared_fields:
        starters.append(f"I studied {shared_fields[0]} too — how are you applying it in your work?")

    if not starters and target.headline:
        starters.append(f"I noticed you work in {target.headline} — what does a typical day look like for you?")
    if not starters:
        starters.append(f"Hi {target.full_name}, great to meet you — what brings you to this event?")

    return starters[:3]
