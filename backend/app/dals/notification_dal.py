"""Data Access Layer for notification logs."""

from uuid import UUID

from app.dals.base_dal import BaseDAL
from app.schemas.notification import NotificationLogCreate, NotificationPreferenceResponse
from supabase import Client


class NotificationDAL(BaseDAL):
    """DAL for notification logs and notification preferences."""

    LOG_TABLE = "notifications"
    PREF_TABLE = "user_notification_preferences"

    def __init__(self, client: Client):
        super().__init__(client)

    async def log(self, data: NotificationLogCreate) -> None:
        """Insert a notification delivery log row."""
        payload = {
            "user_id": str(data.user_id),
            "event_id": str(data.event_id) if data.event_id else None,
            "type": data.type.value,
            "status": data.status.value,
        }
        self.client.table(self.LOG_TABLE).insert(payload).execute()

    async def get_preferences_by_user_id(
        self,
        user_id: UUID,
    ) -> NotificationPreferenceResponse | None:
        """Fetch one user's notification preferences."""
        response = (
            self.client.table(self.PREF_TABLE)
            .select("*")
            .eq("user_id", str(user_id))
            .maybe_single()
            .execute()
        )
        if response.data:
            return NotificationPreferenceResponse(**response.data)
        return None

    async def get_event_update_opt_in_user_ids(self, user_ids: list[UUID]) -> set[UUID]:
        """
        Return users who should receive event update emails.

        Users must have:
        - email_notifications = true
        - event_updates = true

        If a user has no preference row, default to opted-in behavior.
        """
        if not user_ids:
            return set()

        user_id_strings = [str(user_id) for user_id in user_ids]
        response = (
            self.client.table(self.PREF_TABLE)
            .select("user_id,email_notifications,event_updates")
            .in_("user_id", user_id_strings)
            .execute()
        )

        rows = response.data or []
        allowed_from_rows = {
            UUID(row["user_id"])
            for row in rows
            if row.get("user_id")
            and bool(row.get("email_notifications", False))
            and bool(row.get("event_updates", False))
        }
        with_row = {UUID(row["user_id"]) for row in rows if row.get("user_id")}
        missing_row_defaults = {user_id for user_id in user_ids if user_id not in with_row}

        return allowed_from_rows | missing_row_defaults
