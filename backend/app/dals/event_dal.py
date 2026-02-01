"""Data Access Layer for events."""

from uuid import UUID

from app.dals.base_dal import BaseDAL
from app.schemas import EventCreate, EventResponse, EventUpdate
from supabase import Client


class EventDAL(BaseDAL):
    """DAL for event operations."""

    TABLE = "events"

    def __init__(self, client: Client):
        super().__init__(client)

    async def get_by_id(self, event_id: UUID) -> EventResponse | None:
        """
        Get an event by ID.
        RLS restricts to events user is member of or created.
        """
        response = (
            self.client.table(self.TABLE)
            .select("*")
            .eq("event_id", str(event_id))
            .maybe_single()
            .execute()
        )

        if response.data:
            return EventResponse(**response.data)
        return None

    async def get_user_events(self, user_id: UUID) -> list[EventResponse]:
        """
        Get all events a user is a member of.
        """
        # First get event IDs from memberships
        memberships = (
            self.client.table("event_memberships")
            .select("event_id")
            .eq("user_id", str(user_id))
            .execute()
        )

        if not memberships.data:
            return []

        event_ids = [m["event_id"] for m in memberships.data]

        # Then get event details
        response = (
            self.client.table(self.TABLE)
            .select("*")
            .in_("event_id", event_ids)
            .order("starts_at", desc=False)
            .execute()
        )

        return [EventResponse(**event) for event in response.data]

    async def create(self, created_by: UUID, data: EventCreate) -> EventResponse:
        """
        Create a new event.
        """
        insert_data = {
            "created_by": str(created_by),
            **data.model_dump(exclude_none=True),
        }

        # Handle datetime serialization
        if insert_data.get("starts_at"):
            insert_data["starts_at"] = insert_data["starts_at"].isoformat()
        if insert_data.get("ends_at"):
            insert_data["ends_at"] = insert_data["ends_at"].isoformat()

        response = self.client.table(self.TABLE).insert(insert_data).execute()

        return EventResponse(**response.data[0])

    async def update(self, event_id: UUID, data: EventUpdate) -> EventResponse | None:
        """
        Update an event.
        RLS ensures only creator can update.
        """
        update_data = data.model_dump(exclude_none=True)

        if not update_data:
            return await self.get_by_id(event_id)

        # Handle datetime serialization
        if update_data.get("starts_at"):
            update_data["starts_at"] = update_data["starts_at"].isoformat()
        if update_data.get("ends_at"):
            update_data["ends_at"] = update_data["ends_at"].isoformat()

        response = (
            self.client.table(self.TABLE)
            .update(update_data)
            .eq("event_id", str(event_id))
            .execute()
        )

        if response.data:
            return EventResponse(**response.data[0])
        return None

    async def delete(self, event_id: UUID) -> bool:
        """
        Delete an event (soft delete by setting is_active=False).
        """
        response = (
            self.client.table(self.TABLE)
            .update({"is_active": False})
            .eq("event_id", str(event_id))
            .execute()
        )

        return len(response.data) > 0

    async def get_active_events(self) -> list[EventResponse]:
        """
        Get all active events (for discovery/listing).
        Respects RLS - only returns events user can see.
        """
        response = (
            self.client.table(self.TABLE)
            .select("*")
            .eq("is_active", True)
            .order("starts_at", desc=False)
            .execute()
        )

        return [EventResponse(**event) for event in response.data]
