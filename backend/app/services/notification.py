"""Notification service for event update emails and delivery logs."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.config import Settings, get_settings
from app.dals import NotificationDAL
from app.db import get_admin_client
from app.schemas import EventResponse
from app.schemas.notification import NotificationLogCreate, NotificationStatus, NotificationType
from supabase import Client

logger = logging.getLogger(__name__)


JsonDict = Mapping[str, object]


@dataclass(frozen=True)
class NotificationRecipient:
    """Recipient metadata used for sending/logging notifications."""

    user_id: UUID
    email: str


class NotificationService:
    """Send event update notifications and persist delivery logs."""

    def __init__(self, admin_client: Client | None = None, settings: Settings | None = None):
        self.admin_client = admin_client or get_admin_client()
        self.settings = settings or get_settings()
        self.notification_dal = NotificationDAL(self.admin_client)

    async def notify_event_updated(
        self,
        *,
        old_event: EventResponse,
        new_event: EventResponse,
        actor_user_id: UUID,
    ) -> None:
        """Send notifications for event updates when relevant fields changed."""
        should_send, reasons = self.should_send_event_update(
            old_event=old_event, new_event=new_event
        )
        if not should_send:
            return

        recipients = await self._resolve_recipients(
            event_id=new_event.event_id,
            exclude_user_id=actor_user_id,
        )
        if not recipients:
            return

        subject = f"Event updated: {new_event.name}"
        body = self._build_update_email_body(
            old_event=old_event, new_event=new_event, reasons=reasons
        )
        await self._send_and_log(
            recipients=recipients,
            subject=subject,
            body=body,
            event_id=new_event.event_id,
            notification_type=NotificationType.EVENT_UPDATE,
        )

    async def notify_event_deleted(
        self,
        *,
        deleted_event: EventResponse,
        actor_user_id: UUID,
        recipients: list[NotificationRecipient] | None = None,
    ) -> None:
        """Send notifications when an event is deleted."""
        resolved_recipients = recipients or await self._resolve_recipients(
            event_id=deleted_event.event_id,
            exclude_user_id=actor_user_id,
        )
        if not resolved_recipients:
            return

        subject = f"Event deleted: {deleted_event.name}"
        body = self._build_deleted_email_body(deleted_event)
        # `event_id` is intentionally null here because the event is removed.
        await self._send_and_log(
            recipients=resolved_recipients,
            subject=subject,
            body=body,
            event_id=None,
            notification_type=NotificationType.EVENT_UPDATE,
        )

    async def prepare_event_update_recipients(
        self,
        *,
        event_id: UUID,
        actor_user_id: UUID,
    ) -> list[NotificationRecipient]:
        """Resolve opted-in recipients for a specific event."""
        return await self._resolve_recipients(event_id=event_id, exclude_user_id=actor_user_id)

    def should_send_event_update(
        self,
        *,
        old_event: EventResponse,
        new_event: EventResponse,
    ) -> tuple[bool, list[str]]:
        """
        Return whether update notifications should be sent and why.

        Rules:
        - send on time changes (`starts_at` or `ends_at`)
        - send on location change
        - send when event becomes archived (`is_active: true -> false`)
        """
        reasons: list[str] = []
        if not self._datetime_equal(
            old_event.starts_at, new_event.starts_at
        ) or not self._datetime_equal(
            old_event.ends_at,
            new_event.ends_at,
        ):
            reasons.append("time")
        if old_event.location != new_event.location:
            reasons.append("location")
        if old_event.is_active and not new_event.is_active:
            reasons.append("archived")

        return (len(reasons) > 0, reasons)

    @staticmethod
    def _datetime_equal(left: datetime | None, right: datetime | None) -> bool:
        if left is None and right is None:
            return True
        if left is None or right is None:
            return False
        return left == right

    async def _resolve_recipients(
        self,
        *,
        event_id: UUID,
        exclude_user_id: UUID | None = None,
    ) -> list[NotificationRecipient]:
        membership_response = (
            self.admin_client.table("event_memberships")
            .select("user_id")
            .eq("event_id", str(event_id))
            .execute()
        )
        user_ids: list[UUID] = []
        rows = membership_response.data or []
        for row in rows:
            if not isinstance(row, Mapping):
                continue
            row_dict = row
            user_id_raw = row_dict.get("user_id")
            if isinstance(user_id_raw, str):
                user_ids.append(UUID(user_id_raw))
        if exclude_user_id:
            user_ids = [user_id for user_id in user_ids if user_id != exclude_user_id]
        if not user_ids:
            return []

        opted_in_user_ids = set(await self._filter_opted_in_user_ids(user_ids=user_ids))
        if not opted_in_user_ids:
            return []

        recipients: list[NotificationRecipient] = []
        for user_id in user_ids:
            if user_id not in opted_in_user_ids:
                continue
            email = self._get_user_email(user_id)
            if not email:
                continue
            recipients.append(NotificationRecipient(user_id=user_id, email=email))
        return recipients

    async def _filter_opted_in_user_ids(self, *, user_ids: list[UUID]) -> list[UUID]:
        """
        Keep users with both email_notifications and event_updates enabled.

        Missing preference rows default to opted-in behavior.
        """
        if not user_ids:
            return []

        try:
            return list(await self.notification_dal.get_event_update_opt_in_user_ids(user_ids))
        except Exception as exc:
            logger.warning(
                (
                    "Failed to read notification preferences, "
                    "defaulting all recipients to opted-in: %s"
                ),
                exc,
            )
            return user_ids

    def _get_user_email(self, user_id: UUID) -> str | None:
        try:
            response = self.admin_client.auth.admin.get_user_by_id(str(user_id))
        except Exception as exc:
            logger.warning("Failed to fetch auth user=%s for notification email: %s", user_id, exc)
            return None

        user_obj: object = getattr(response, "user", None)
        if user_obj is None and isinstance(response, Mapping):
            user_obj = response.get("user")

        if user_obj is None:
            return None

        email: object = getattr(user_obj, "email", None)
        if email is None and isinstance(user_obj, Mapping):
            email = user_obj.get("email")
        if not email:
            return None
        return str(email)

    async def _send_and_log(
        self,
        *,
        recipients: list[NotificationRecipient],
        subject: str,
        body: str,
        event_id: UUID | None,
        notification_type: NotificationType,
    ) -> None:
        for recipient in recipients:
            sent = await self._send_email(
                recipient_email=recipient.email, subject=subject, body=body
            )
            await self._log_notification(
                user_id=recipient.user_id,
                event_id=event_id,
                notification_type=notification_type,
                status=NotificationStatus.SENT if sent else NotificationStatus.FAILED,
            )

    async def _send_email(self, *, recipient_email: str, subject: str, body: str) -> bool:
        if not self.settings.mail_enabled:
            return False

        try:
            # Lazy import prevents app startup failures if fastapi-mail
            # is not installed in local dev environments yet.
            from app.services.email import EmailConfigurationError, EmailService

            await EmailService(settings=self.settings).send_email(
                recipients=[recipient_email],
                subject=subject,
                body=body,
                is_html=True,
            )
            return True
        except (EmailConfigurationError, Exception) as exc:
            logger.warning("Failed to send notification email to %s: %s", recipient_email, exc)
            return False

    async def _log_notification(
        self,
        *,
        user_id: UUID,
        event_id: UUID | None,
        notification_type: NotificationType,
        status: NotificationStatus,
    ) -> None:
        try:
            await self.notification_dal.log(
                NotificationLogCreate(
                    user_id=user_id,
                    event_id=event_id,
                    type=notification_type,
                    status=status,
                )
            )
        except Exception as exc:
            logger.warning("Failed to log notification for user=%s: %s", user_id, exc)

    def _build_update_email_body(
        self,
        *,
        old_event: EventResponse,
        new_event: EventResponse,
        reasons: list[str],
    ) -> str:
        lines: list[str] = [f"<p><strong>{new_event.name}</strong> has been updated.</p>", "<ul>"]
        if "time" in reasons:
            old_time = self._format_time(old_event.starts_at, old_event.ends_at)
            new_time = self._format_time(new_event.starts_at, new_event.ends_at)
            lines.append(f"<li><strong>Time:</strong> {old_time} -> {new_time}</li>")
        if "location" in reasons:
            lines.append(
                (
                    f"<li><strong>Location:</strong> {old_event.location or 'TBD'}"
                    f" -> {new_event.location or 'TBD'}</li>"
                )
            )
        if "archived" in reasons:
            lines.append("<li><strong>Status:</strong> This event has been archived.</li>")
        lines.append("</ul>")
        return "".join(lines)

    def _build_deleted_email_body(self, event: EventResponse) -> str:
        return (
            f"<p>The event <strong>{event.name}</strong> has been deleted.</p>"
            f"<p>Scheduled time: {self._format_time(event.starts_at, event.ends_at)}</p>"
            f"<p>Location: {event.location or 'TBD'}</p>"
        )

    @staticmethod
    def _format_time(starts_at: datetime | None, ends_at: datetime | None) -> str:
        if starts_at is None and ends_at is None:
            return "TBD"
        if starts_at and ends_at:
            return f"{starts_at.isoformat()} to {ends_at.isoformat()}"
        if starts_at:
            return f"Starts {starts_at.isoformat()}"
        if ends_at:
            return f"Ends {ends_at.isoformat()}"
        return "TBD"
