"""Generate concise profile summaries, with optional DSPy support."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

from app.config import Settings, get_settings
from app.schemas import ProfileResponse

DEFAULT_SUMMARY_MODEL = "openai/gpt-4o-mini"


class ProfileSummaryError(Exception):
    """Raised when summary generation fails."""


@dataclass(frozen=True)
class ProfileSummaryResult:
    """Generated profile snippets for cards and profile pages."""

    one_liner: str
    summary: str
    provider: str


class ProfileSummaryService:
    """Build one-line and expanded summaries from profile data."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

    def generate(self, profile: ProfileResponse) -> ProfileSummaryResult:
        """Generate summary text based on configured provider."""
        provider = self.settings.profile_summary_provider.strip().lower()
        if provider not in {"auto", "dspy", "template"}:
            provider = "auto"

        if provider in {"auto", "dspy"}:
            try:
                one_liner, summary = self._generate_with_dspy(profile)
                return ProfileSummaryResult(
                    one_liner=_truncate(one_liner, 180),
                    summary=_truncate(summary, 1200),
                    provider="dspy",
                )
            except ProfileSummaryError:
                if provider == "dspy":
                    raise

        one_liner, summary = self._generate_with_template(profile)
        return ProfileSummaryResult(
            one_liner=_truncate(one_liner, 180),
            summary=_truncate(summary, 1200),
            provider="template",
        )

    def _generate_with_dspy(self, profile: ProfileResponse) -> tuple[str, str]:
        """Generate summaries with DSPy."""
        api_key = self.settings.openai_api_key
        if not api_key:
            raise ProfileSummaryError("OPENAI_API_KEY is not configured for DSPy summaries.")

        model = self.settings.profile_summary_model or DEFAULT_SUMMARY_MODEL
        context = _build_profile_context(profile)

        try:
            predictor = _get_dspy_predictor(model, api_key)
            prediction = predictor(profile_context=context)
        except Exception as exc:  # pragma: no cover - network/runtime dependent
            raise ProfileSummaryError(f"DSPy generation failed: {exc}") from exc

        one_liner = str(getattr(prediction, "one_liner", "")).strip()
        summary = str(getattr(prediction, "summary", "")).strip()
        if not one_liner or not summary:
            raise ProfileSummaryError("DSPy returned empty summary fields.")

        return one_liner, summary

    @staticmethod
    def _generate_with_template(profile: ProfileResponse) -> tuple[str, str]:
        """Generate deterministic fallback summaries."""
        headline = (profile.headline or "").strip()
        company = (profile.company or "").strip()
        major = (profile.major or "").strip()
        location = (profile.location or "").strip()
        bio = (profile.bio or "").strip()

        role_fragment = headline or f"professional at {company}" if company else "professional"
        if major and not headline:
            role_fragment = f"{major} student and {role_fragment}"

        location_fragment = f" based in {location}" if location else ""
        one_liner = f"{profile.full_name} is a {role_fragment}{location_fragment}."

        experiences = profile.experiences or []
        education = profile.education or []

        summary_parts: list[str] = []
        if bio:
            summary_parts.append(bio)
        else:
            summary_parts.append(one_liner)

        if experiences:
            latest = experiences[0]
            title = str(latest.get("title") or "").strip()
            exp_company = str(latest.get("company") or "").strip()
            if title and exp_company:
                summary_parts.append(f"Most recently: {title} at {exp_company}.")
            elif title:
                summary_parts.append(f"Most recently: {title}.")
            elif exp_company:
                summary_parts.append(f"Most recently associated with {exp_company}.")

        if education:
            latest_edu = education[0]
            school = str(latest_edu.get("school") or "").strip()
            degree = str(latest_edu.get("degree") or "").strip()
            if school and degree:
                summary_parts.append(f"Education: {degree} at {school}.")
            elif school:
                summary_parts.append(f"Education: {school}.")

        summary = " ".join(part.strip() for part in summary_parts if part.strip())
        return one_liner, summary


def _build_profile_context(profile: ProfileResponse) -> str:
    """Serialize profile data into an LLM-friendly prompt context."""
    experiences = profile.experiences or []
    education = profile.education or []

    lines = [
        f"Name: {profile.full_name}",
        f"Headline: {profile.headline or ''}",
        f"Location: {profile.location or ''}",
        f"Bio: {profile.bio or ''}",
        f"Company: {profile.company or ''}",
        f"Major: {profile.major or ''}",
        f"Graduation Year: {profile.graduation_year or ''}",
        "Experience:",
    ]
    for item in experiences[:6]:
        lines.append(
            (
                f"- title={item.get('title') or ''}; company={item.get('company') or ''}; "
                f"start={item.get('start_date') or ''}; end={item.get('end_date') or ''}"
            )
        )

    lines.append("Education:")
    for item in education[:4]:
        lines.append(
            (
                f"- school={item.get('school') or ''}; degree={item.get('degree') or ''}; "
                f"field={item.get('field_of_study') or ''}; "
                f"start={item.get('start_date') or ''}; end={item.get('end_date') or ''}"
            )
        )

    return "\n".join(lines)


def _truncate(text: str, max_len: int) -> str:
    """Trim text to maximum length without returning an empty string."""
    cleaned = text.strip()
    if len(cleaned) <= max_len:
        return cleaned
    return cleaned[: max_len - 1].rstrip() + "…"


@lru_cache(maxsize=4)
def _get_dspy_predictor(model: str, api_key: str):  # pragma: no cover - runtime integration
    """Lazily configure DSPy predictor."""
    cache_dir = os.environ.setdefault("DSPY_CACHEDIR", "/tmp/dspy_cache")
    os.makedirs(cache_dir, exist_ok=True)

    try:
        import dspy
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise ProfileSummaryError(
            "DSPy is not installed. Install dspy-ai to enable AI summaries."
        ) from exc

    class ProfileSummarySignature(dspy.Signature):
        """Summarize a profile into short and long forms."""

        profile_context = dspy.InputField()
        one_liner = dspy.OutputField(desc="One sentence, <= 20 words, professional and specific.")
        summary = dspy.OutputField(
            desc="Two to four sentences, <= 120 words, readable profile summary."
        )

    lm = dspy.LM(model=model, api_key=api_key)
    dspy.configure(lm=lm)
    return dspy.Predict(ProfileSummarySignature)
