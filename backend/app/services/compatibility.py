"""Compute compatibility scores and generate conversation starters between two profiles."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from functools import lru_cache

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
            viewer.location
            and target.location
            and viewer.location.strip().lower() == target.location.strip().lower()
        )

        rule_score = min(
            100.0,
            len(shared_companies) * 30.0
            + len(shared_schools) * 25.0
            + len(shared_fields) * 20.0
            + (10.0 if same_location else 0.0),
        )

        dspy_score, starters = self._generate_starters(
            viewer, target, shared_companies, shared_schools, shared_fields
        )

        # Prefer the DSPy score (richer semantic judgment); fall back to rule-based.
        score = dspy_score if dspy_score is not None else rule_score

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
    ) -> tuple[float | None, list[str]]:
        """Return (dspy_score_or_None, starters)."""
        settings = get_settings()
        if settings.openai_api_key:
            try:
                return _generate_with_dspy(
                    model=settings.profile_summary_model,
                    api_key=settings.openai_api_key,
                    viewer=viewer,
                    target=target,
                    shared_companies=shared_companies,
                    shared_schools=shared_schools,
                    shared_fields=shared_fields,
                )
            except Exception as exc:
                logger.warning("DSPy conversation starter generation failed: %s", exc)

        return None, _template_starters(target, shared_companies, shared_schools, shared_fields)


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


def _build_context(
    viewer: ProfileResponse,
    target: ProfileResponse,
    shared_companies: list[str],
    shared_schools: list[str],
    shared_fields: list[str],
) -> str:
    viewer_name = viewer.full_name or "an attendee"
    parts = [f"You are {viewer_name}."]

    target_desc = target.full_name or "someone"
    if target.headline or target.company:
        target_desc += f" ({', '.join(x for x in [target.headline, target.company] if x)})"
    parts.append(f"You just met {target_desc} at a networking event.")

    if target.bio:
        parts.append(f"Their bio: {target.bio[:400]}")
    if target.major:
        parts.append(f"Their field: {target.major}.")
    if target.location:
        parts.append(f"Based in: {target.location}.")
    if target.education:
        schools = [str(e.get("school") or "") for e in (target.education or []) if e.get("school")]
        if schools:
            parts.append(f"Studied at: {', '.join(schools[:2])}.")
    if target.experiences:
        recent = [
            str(e.get("company") or "") for e in (target.experiences or []) if e.get("company")
        ]
        if recent:
            parts.append(f"Has worked at: {', '.join(recent[:3])}.")
    if target.profile_one_liner:
        parts.append(f"In their own words: {target.profile_one_liner}")

    if shared_companies:
        parts.append(f"You've both worked at: {', '.join(shared_companies)}.")
    if shared_schools:
        parts.append(f"You both attended: {', '.join(shared_schools)}.")
    if shared_fields:
        parts.append(f"You share fields of study: {', '.join(shared_fields)}.")

    return " ".join(p for p in parts if p.strip())


def _generate_with_dspy(
    model: str,
    api_key: str,
    viewer: ProfileResponse,
    target: ProfileResponse,
    shared_companies: list[str],
    shared_schools: list[str],
    shared_fields: list[str],
) -> tuple[float | None, list[str]]:
    """Return (score_or_None, starters). Score is None if DSPy couldn't parse it."""
    predictor = _get_dspy_predictor(model, api_key)
    context = _build_context(viewer, target, shared_companies, shared_schools, shared_fields)
    prediction = predictor(context=context)

    raw_score = str(getattr(prediction, "compatibility_score", "")).strip()
    dspy_score: float | None = None
    try:
        dspy_score = max(0.0, min(100.0, float(raw_score)))
    except (ValueError, TypeError):
        pass

    starters = [str(getattr(prediction, f"starter_{i}", "")).strip() for i in range(1, 4)]
    starters = [s for s in starters if s]
    if not starters:
        raise ValueError("DSPy returned empty starter fields.")
    return dspy_score, starters


@lru_cache(maxsize=4)
def _get_dspy_predictor(model: str, api_key: str):  # pragma: no cover - runtime integration
    cache_dir = os.environ.setdefault("DSPY_CACHEDIR", "/tmp/dspy_cache")
    os.makedirs(cache_dir, exist_ok=True)

    try:
        import dspy
    except ImportError as exc:
        raise RuntimeError("DSPy is not installed. Install dspy-ai to enable AI starters.") from exc

    class CompatibilitySignature(dspy.Signature):
        """Score compatibility and generate ice-breaker starters for a networking event."""

        context = dspy.InputField(
            desc="Profile context: who you are, who you just met, and any shared background."
        )
        compatibility_score = dspy.OutputField(
            desc="Integer from 0 to 100: how valuable this connection would be professionally."
        )
        starter_1 = dspy.OutputField(
            desc="First starter — one sentence, first-person, specific to this person."
        )
        starter_2 = dspy.OutputField(
            desc="Second starter — one sentence, first-person, specific to this person."
        )
        starter_3 = dspy.OutputField(
            desc="Third conversation starter — one sentence, first-person, specific to this person."
        )

    lm = dspy.LM(model=model, api_key=api_key)
    dspy.configure(lm=lm)
    return dspy.Predict(CompatibilitySignature)


def _template_starters(
    target: ProfileResponse,
    shared_companies: list[str],
    shared_schools: list[str],
    shared_fields: list[str],
) -> list[str]:
    starters: list[str] = []

    if shared_companies:
        starters.append(
            f"I see we've both worked at {shared_companies[0]}"
            " — what was your experience like there?"
        )
    if shared_schools:
        starters.append(f"Did you enjoy your time at {shared_schools[0]}?")
    if shared_fields:
        starters.append(f"I studied {shared_fields[0]} too — how are you applying it in your work?")

    if not starters and target.headline:
        starters.append(
            f"I noticed you work in {target.headline} — what does a typical day look like for you?"
        )
    if not starters:
        starters.append(
            f"Hi {target.full_name}, great to meet you — what brings you to this event?"
        )

    return starters[:3]
