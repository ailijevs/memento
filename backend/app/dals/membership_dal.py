"""Data Access Layer for event memberships."""
from datetime import datetime, timezone
from uuid import UUID

from supabase import Client

from app.dals.base_dal import BaseDAL
from app.schemas import MembershipCreate, MembershipUpdate, MembershipResponse


class MembershipDAL(BaseDAL):
    """DAL for event membership operations."""

    TABLE = "event_memberships"

    def __init__(self, client: Client):
        super().__init__(client)

    async def get(self, event_id: UUID, user_id: UUID) -> MembershipResponse | None:
        """
        Get a specific membership.
        """
        response = (
            self.client.table(self.TABLE)
            .select("*")
            .eq("event_id", str(event_id))
            .eq("user_id", str(user_id))
            .maybe_single()
            .execute()
        )

        if response.data:
            return MembershipResponse(**response.data)
        return None

    async def get_event_members(self, event_id: UUID) -> list[MembershipResponse]:
        """
        Get all memberships for an event.
        RLS ensures caller is also a member.
        """
        response = (
            self.client.table(self.TABLE)
            .select("*")
            .eq("event_id", str(event_id))
            .order("created_at", desc=False)
            .execute()
        )

        return [MembershipResponse(**m) for m in response.data]

    async def get_user_memberships(self, user_id: UUID) -> list[MembershipResponse]:
        """
        Get all memberships for a user.
        """
        response = (
            self.client.table(self.TABLE)
            .select("*")
            .eq("user_id", str(user_id))
            .order("created_at", desc=False)
            .execute()
        )

        return [MembershipResponse(**m) for m in response.data]

    async def join_event(self, user_id: UUID, data: MembershipCreate) -> MembershipResponse:
        """
        Join an event (create membership).
        RLS ensures user can only create their own membership.
        """
        insert_data = {
            "event_id": str(data.event_id),
            "user_id": str(user_id),
            "role": data.role.value,
        }

        response = (
            self.client.table(self.TABLE)
            .insert(insert_data)
            .execute()
        )

        return MembershipResponse(**response.data[0])

    async def update(
        self, event_id: UUID, user_id: UUID, data: MembershipUpdate
    ) -> MembershipResponse | None:
        """
        Update a membership.
        """
        update_data = {}

        if data.role is not None:
            update_data["role"] = data.role.value
        if data.checked_in_at is not None:
            update_data["checked_in_at"] = data.checked_in_at.isoformat()

        if not update_data:
            return await self.get(event_id, user_id)

        response = (
            self.client.table(self.TABLE)
            .update(update_data)
            .eq("event_id", str(event_id))
            .eq("user_id", str(user_id))
            .execute()
        )

        if response.data:
            return MembershipResponse(**response.data[0])
        return None

    async def check_in(self, event_id: UUID, user_id: UUID) -> MembershipResponse | None:
        """
        Check in a user to an event.
        """
        response = (
            self.client.table(self.TABLE)
            .update({"checked_in_at": datetime.now(timezone.utc).isoformat()})
            .eq("event_id", str(event_id))
            .eq("user_id", str(user_id))
            .execute()
        )

        if response.data:
            return MembershipResponse(**response.data[0])
        return None

    async def leave_event(self, event_id: UUID, user_id: UUID) -> bool:
        """
        Leave an event (delete membership).
        """
        response = (
            self.client.table(self.TABLE)
            .delete()
            .eq("event_id", str(event_id))
            .eq("user_id", str(user_id))
            .execute()
        )

        return len(response.data) > 0

    async def is_member(self, event_id: UUID, user_id: UUID) -> bool:
        """
        Check if a user is a member of an event.
        """
        membership = await self.get(event_id, user_id)
        return membership is not None
