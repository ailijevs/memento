"""Data Access Layer for event consents."""

from datetime import datetime, timezone
from uuid import UUID

from app.dals.base_dal import BaseDAL
from app.schemas import ConsentCreate, ConsentResponse, ConsentUpdate
from supabase import Client


class ConsentDAL(BaseDAL):
    """DAL for event consent operations."""

    TABLE = "event_consents"

    def __init__(self, client: Client):
        super().__init__(client)

    async def get(self, event_id: UUID, user_id: UUID) -> ConsentResponse | None:
        """
        Get consent settings for a user in an event.
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
            return ConsentResponse(**response.data)
        return None

    async def get_user_consents(self, user_id: UUID) -> list[ConsentResponse]:
        """
        Get all consent settings for a user across events.
        """
        response = self.client.table(self.TABLE).select("*").eq("user_id", str(user_id)).execute()

        return [ConsentResponse(**c) for c in response.data]

    async def create(self, user_id: UUID, data: ConsentCreate) -> ConsentResponse:
        """
        Create consent settings for an event.
        Called when user joins an event.
        """
        now = datetime.now(timezone.utc).isoformat()

        insert_data = {
            "event_id": str(data.event_id),
            "user_id": str(user_id),
            "allow_profile_display": data.allow_profile_display,
            "allow_recognition": data.allow_recognition,
            "consented_at": now if (data.allow_profile_display or data.allow_recognition) else None,
        }

        response = self.client.table(self.TABLE).insert(insert_data).execute()

        return ConsentResponse(**response.data[0])

    async def update(
        self, event_id: UUID, user_id: UUID, data: ConsentUpdate
    ) -> ConsentResponse | None:
        """
        Update consent settings.
        Tracks consent/revocation timestamps.
        """
        # First get current consent state
        current = await self.get(event_id, user_id)
        if not current:
            return None

        update_data = {}
        now = datetime.now(timezone.utc).isoformat()

        # Handle profile display consent changes
        if data.allow_profile_display is not None:
            update_data["allow_profile_display"] = data.allow_profile_display
            if data.allow_profile_display and not current.allow_profile_display:
                # Granting consent
                update_data["consented_at"] = now
                update_data["revoked_at"] = None
            elif not data.allow_profile_display and current.allow_profile_display:
                # Revoking consent
                update_data["revoked_at"] = now

        # Handle recognition consent changes
        if data.allow_recognition is not None:
            update_data["allow_recognition"] = data.allow_recognition
            # Similar logic for recognition consent
            if data.allow_recognition and not current.allow_recognition:
                if "consented_at" not in update_data:
                    update_data["consented_at"] = now
                update_data["revoked_at"] = None

        if not update_data:
            return current

        response = (
            self.client.table(self.TABLE)
            .update(update_data)
            .eq("event_id", str(event_id))
            .eq("user_id", str(user_id))
            .execute()
        )

        if response.data:
            return ConsentResponse(**response.data[0])
        return None

    async def grant_all(self, event_id: UUID, user_id: UUID) -> ConsentResponse | None:
        """
        Grant all consent permissions.
        """
        return await self.update(
            event_id,
            user_id,
            ConsentUpdate(allow_profile_display=True, allow_recognition=True),
        )

    async def revoke_all(self, event_id: UUID, user_id: UUID) -> ConsentResponse | None:
        """
        Revoke all consent permissions.
        """
        now = datetime.now(timezone.utc).isoformat()

        response = (
            self.client.table(self.TABLE)
            .update(
                {
                    "allow_profile_display": False,
                    "allow_recognition": False,
                    "revoked_at": now,
                }
            )
            .eq("event_id", str(event_id))
            .eq("user_id", str(user_id))
            .execute()
        )

        if response.data:
            return ConsentResponse(**response.data[0])
        return None

    async def delete(self, event_id: UUID, user_id: UUID) -> bool:
        """
        Delete consent record (typically when leaving event).
        """
        response = (
            self.client.table(self.TABLE)
            .delete()
            .eq("event_id", str(event_id))
            .eq("user_id", str(user_id))
            .execute()
        )

        return len(response.data) > 0
