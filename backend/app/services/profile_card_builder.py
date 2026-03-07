"""Builds frontend-friendly profile cards from recognition matches."""

from __future__ import annotations

import logging
from typing import Any

from app.schemas.recognition import ProfileCard

logger = logging.getLogger(__name__)


class ProfileCardBuilder:
    """Resolves Rekognition matches into profile cards for the frontend.

    Takes raw match data (user_id, similarity) and fetches the matched
    user's profile from Supabase, respecting consent when an event_id
    is provided.
    """

    def __init__(self, admin_client: Any) -> None:
        self.client = admin_client

    def build_cards(
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

            if event_id and not self._has_display_consent(user_id, event_id):
                logger.debug(
                    "Skipping user %s: no display consent for event %s",
                    user_id,
                    event_id,
                )
                continue

            card = self._build_single_card(
                user_id=user_id,
                similarity=match.get("similarity", 0.0),
            )
            if card:
                cards.append(card)

        return cards

    def _build_single_card(
        self,
        user_id: str,
        similarity: float,
    ) -> ProfileCard | None:
        """Fetch a user's profile and build a ProfileCard."""
        try:
            response = (
                self.client.table("profiles")
                .select(
                    "user_id, full_name, headline, bio, company, "
                    "photo_path, linkedin_url, profile_one_liner"
                )
                .eq("user_id", user_id)
                .maybe_single()
                .execute()
            )

            if not response or not response.data:
                logger.warning("No profile found for user_id=%s", user_id)
                return None

            profile = response.data
            return ProfileCard(
                user_id=str(profile["user_id"]),
                full_name=profile.get("full_name", "Unknown"),
                headline=profile.get("headline"),
                bio=profile.get("bio"),
                company=profile.get("company"),
                photo_path=profile.get("photo_path"),
                linkedin_url=profile.get("linkedin_url"),
                profile_one_liner=profile.get("profile_one_liner"),
                similarity=round(similarity, 2),
            )

        except Exception as e:
            logger.error(
                "Failed to build profile card for user %s: %s",
                user_id,
                e,
            )
            return None

    def _has_display_consent(self, user_id: str, event_id: str) -> bool:
        """Check if user has allow_profile_display for the given event."""
        try:
            response = (
                self.client.table("event_consents")
                .select("allow_profile_display")
                .eq("event_id", event_id)
                .eq("user_id", user_id)
                .maybe_single()
                .execute()
            )

            if not response or not response.data:
                return False

            return bool(response.data.get("allow_profile_display", False))

        except Exception as e:
            logger.error(
                "Failed to check consent for user %s event %s: %s",
                user_id,
                event_id,
                e,
            )
            return False
