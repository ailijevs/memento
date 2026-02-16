"""Data Access Layer for user profiles."""

from uuid import UUID

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
                .execute()
            )

            if response.data and len(response.data) > 0:
                return ProfileResponse(**response.data[0])
            return None
        except Exception:
            # Handle case where profile doesn't exist or RLS blocks access
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
        Only returns profiles where user has consented to display.
        """
        response = self.client.rpc("get_event_directory", {"p_event_id": str(event_id)}).execute()

        return [ProfileDirectoryEntry(**row) for row in response.data]
