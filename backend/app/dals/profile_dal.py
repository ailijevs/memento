"""Data Access Layer for user profiles."""

import calendar
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from postgrest.exceptions import APIError

from app.dals.base_dal import BaseDAL
from app.schemas import (
    ProfileCreate,
    ProfileDirectoryEntry,
    ProfileResponse,
    ProfileUpdate,
)
from supabase import Client


class ProfileDAL(BaseDAL):
    """DAL for profile operations."""

    TABLE = "profiles"

    def __init__(self, client: Client):
        super().__init__(client)

    async def get_by_user_id(self, user_id: UUID) -> ProfileResponse | None:
        """
        Get a profile by user ID.
        RLS will enforce visibility rules.
        """
        try:
            response = (
                self.client.table(self.TABLE)
                .select("*")
                .eq("user_id", str(user_id))
                .maybe_single()
                .execute()
            )
        except APIError as exc:
            # postgrest-py may raise a 204 "Missing response" when no row exists.
            if str(exc.code) == "204":
                return None
            raise

        if response and response.data:
            return ProfileResponse(**response.data)
        return None

    async def create(self, user_id: UUID, data: ProfileCreate) -> ProfileResponse:
        """
        Create a new profile for a user.
        """
        insert_data = {
            "user_id": str(user_id),
            **data.model_dump(exclude_none=True),
        }

        response = self.client.table(self.TABLE).insert(insert_data).execute()

        return ProfileResponse(**response.data[0])

    async def update(self, user_id: UUID, data: ProfileUpdate) -> ProfileResponse | None:
        """
        Update a user's profile.
        Only non-None fields are updated.
        """
        update_data = data.model_dump(exclude_none=True)

        if not update_data:
            # Nothing to update, return current profile
            return await self.get_by_user_id(user_id)

        response = (
            self.client.table(self.TABLE).update(update_data).eq("user_id", str(user_id)).execute()
        )

        if response.data:
            return ProfileResponse(**response.data[0])
        return None

    async def delete(self, user_id: UUID) -> bool:
        """
        Delete a user's profile.
        """
        response = self.client.table(self.TABLE).delete().eq("user_id", str(user_id)).execute()

        return len(response.data) > 0

    async def get_event_directory(self, event_id: UUID) -> list[ProfileDirectoryEntry]:
        """
        Get the directory of profiles for an event.
        Uses the get_event_directory SQL function.
        """
        response = self.client.rpc("get_event_directory", {"p_event_id": str(event_id)}).execute()
        entries: list[ProfileDirectoryEntry] = []
        for row in response.data:
            entries.append(
                ProfileDirectoryEntry(
                    user_id=row["user_id"],
                    full_name=row["full_name"],
                    headline=row.get("headline"),
                    company=row.get("company"),
                    school=_extract_current_school(row.get("education")),
                    major=row.get("major"),
                    photo_path=row.get("photo_path"),
                )
            )
        return entries

    async def update_generated_summary(
        self,
        user_id: UUID,
        *,
        profile_one_liner: str,
        profile_summary: str,
        summary_provider: str,
    ) -> ProfileResponse | None:
        """Persist generated profile summary fields."""
        update_data = {
            "profile_one_liner": profile_one_liner,
            "profile_summary": profile_summary,
            "summary_provider": summary_provider,
            "summary_updated_at": datetime.now(timezone.utc).isoformat(),
        }
        response = (
            self.client.table(self.TABLE).update(update_data).eq("user_id", str(user_id)).execute()
        )
        if response.data:
            return ProfileResponse(**response.data[0])
        return None


def _extract_current_school(education: Any) -> str | None:
    """
    Return the school from the most recent education entry where the user is
    still attending (no end_date or end_date in the future).
    """
    if not isinstance(education, list):
        return None

    now = datetime.now(timezone.utc)
    current_entries: list[tuple[datetime, str]] = []

    for entry in education:
        if not isinstance(entry, dict):
            continue

        school = entry.get("school")
        if not isinstance(school, str) or not school.strip():
            continue

        end_date = _parse_education_date(entry.get("end_date"), end_of_period=True)
        if end_date is not None and end_date < now:
            continue

        start_date = _parse_education_date(entry.get("start_date")) or datetime.min.replace(
            tzinfo=timezone.utc
        )
        current_entries.append((start_date, school.strip()))

    if not current_entries:
        return None

    most_recent = max(current_entries, key=lambda item: item[0])
    return most_recent[1]


def _parse_education_date(value: Any, *, end_of_period: bool = False) -> datetime | None:
    """
    Parse education date strings.

    Supports:
    - YYYY-MM
    - YYYY-MM-DD
    - ISO datetime strings
    """
    if not isinstance(value, str) or not value.strip():
        return None

    text = value.strip()

    # Month precision date (e.g. "2026-05")
    if len(text) == 7 and text[4] == "-":
        try:
            year = int(text[0:4])
            month = int(text[5:7])
            if month < 1 or month > 12:
                return None
        except ValueError:
            return None

        if end_of_period:
            last_day = calendar.monthrange(year, month)[1]
            return datetime(year, month, last_day, 23, 59, 59, tzinfo=timezone.utc)
        return datetime(year, month, 1, tzinfo=timezone.utc)

    text = text.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
