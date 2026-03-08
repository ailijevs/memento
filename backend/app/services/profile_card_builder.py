"""Builds frontend-friendly profile cards from recognition matches."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from app.dals.consent_dal import ConsentDAL
from app.dals.profile_dal import ProfileDAL
from app.schemas.recognition import ProfileCard

logger = logging.getLogger(__name__)


class ProfileCardBuilder:
    """Resolves Rekognition matches into profile cards for the frontend.

    Uses DAL classes for all database access to keep queries organized
    and consistent with the rest of the codebase.
    """

    def __init__(self, admin_client: Any) -> None:
        self.profile_dal = ProfileDAL(admin_client)
        self.consent_dal = ConsentDAL(admin_client)

    async def build_cards(
        self,
        matches: list[dict[str, Any]],
        event_id: str | None = None,
    ) -> list[ProfileCard]:
        """Build profile cards for a list of Rekognition matches.

        Args:
            matches: Raw match dicts with user_id, similarity, etc.
            event_id: If provided, only return cards for users who
                      have allow_profile_display=True for this event.

        Returns:
            List of ProfileCard objects ready for frontend consumption.
        """
        cards: list[ProfileCard] = []

        for match in matches:
            user_id = match.get("user_id")
            if not user_id:
                continue

            if event_id:
                has_consent = await self._has_display_consent(user_id, event_id)
                if not has_consent:
                    logger.debug(
                        "Skipping user %s: no display consent for event %s",
                        user_id,
                        event_id,
                    )
                    continue

            card = await self._build_single_card(
                user_id=user_id,
                face_similarity=match.get("similarity", 0.0),
            )
            if card:
                cards.append(card)

        return cards

    async def _build_single_card(
        self,
        user_id: str,
        face_similarity: float,
    ) -> ProfileCard | None:
        """Fetch a user's profile via ProfileDAL and build a ProfileCard."""
        try:
            profile = await self.profile_dal.get_by_user_id(UUID(user_id))

            if not profile:
                logger.warning("No profile found for user_id=%s", user_id)
                return None

            return ProfileCard(
                user_id=str(profile.user_id),
                full_name=profile.full_name,
                headline=profile.headline,
                company=profile.company,
                photo_path=profile.photo_path,
                profile_one_liner=profile.profile_one_liner,
                face_similarity=round(face_similarity, 2),
                experience_similarity=None,
                bio=profile.bio,
                location=profile.location,
                major=profile.major,
                graduation_year=profile.graduation_year,
                linkedin_url=profile.linkedin_url,
                profile_summary=profile.profile_summary,
                experiences=profile.experiences,
                education=profile.education,
            )

        except Exception as e:
            logger.error(
                "Failed to build profile card for user %s: %s",
                user_id,
                e,
            )
            return None

    async def _has_display_consent(self, user_id: str, event_id: str) -> bool:
        """Check consent via ConsentDAL."""
        try:
            consent = await self.consent_dal.get(
                event_id=UUID(event_id),
                user_id=UUID(user_id),
            )
            if not consent:
                return False
            return bool(consent.allow_profile_display)

        except Exception as e:
            logger.error(
                "Failed to check consent for user %s event %s: %s",
                user_id,
                event_id,
                e,
            )
            return False
