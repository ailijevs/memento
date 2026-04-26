"""Notification service for event update emails and delivery logs."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from uuid import UUID
from zoneinfo import ZoneInfo

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.config import Settings, get_settings
from app.dals import NotificationDAL
from app.db import get_admin_client
from app.schemas import EventResponse
from app.schemas.notification import NotificationLogCreate, NotificationStatus, NotificationType
from supabase import Client

logger = logging.getLogger(__name__)

_EMAIL_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates" / "emails"
_EMAIL_TEMPLATE_ENV = Environment(
    loader=FileSystemLoader(str(_EMAIL_TEMPLATE_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
)
_APP_BRAND_NAME = "Memento"
_EASTERN_TZ = ZoneInfo("America/New_York")


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

    async def notify_host_message(
        self,
        *,
        event: EventResponse,
        actor_user_id: UUID,
        subject: str,
        message: str,
        recipients: list[NotificationRecipient] | None = None,
    ) -> None:
        """Send a host-authored message to opted-in event members."""
        logger.info(
            (
                "notify_host_message called for event=%s actor_user=%s "
                "subject=%r provided_recipient_count=%s"
            ),
            event.event_id,
            actor_user_id,
            subject,
            len(recipients) if recipients is not None else None,
        )
        resolved_recipients = recipients or await self._resolve_recipients(
            event_id=event.event_id,
            exclude_user_id=actor_user_id,
            notification_type=NotificationType.HOST_MESSAGE,
        )
        if not resolved_recipients:
            logger.warning(
                "No host message recipients resolved for event=%s actor_user=%s",
                event.event_id,
                actor_user_id,
            )
            return

        body = self._build_host_message_email_body(
            event=event,
            message=message,
        )
        logger.info(
            "Sending host message for event=%s actor_user=%s resolved_recipient_count=%s",
            event.event_id,
            actor_user_id,
            len(resolved_recipients),
        )
        await self._send_and_log(
            recipients=resolved_recipients,
            subject=subject,
            body=body,
            event_id=event.event_id,
            notification_type=NotificationType.HOST_MESSAGE,
        )

    async def prepare_event_update_recipients(
        self,
        *,
        event_id: UUID,
        actor_user_id: UUID,
    ) -> list[NotificationRecipient]:
        """Resolve opted-in recipients for a specific event."""
        return await self._resolve_recipients(event_id=event_id, exclude_user_id=actor_user_id)

    async def prepare_host_message_recipients(
        self,
        *,
        event_id: UUID,
        actor_user_id: UUID,
    ) -> list[NotificationRecipient]:
        """Resolve recipients for organizer-sent messages for a specific event."""
        return await self._resolve_recipients(
            event_id=event_id,
            exclude_user_id=actor_user_id,
            notification_type=NotificationType.HOST_MESSAGE,
        )

    def should_send_event_update(
        self,
        *,
        old_event: EventResponse,
        new_event: EventResponse,
    ) -> tuple[bool, list[str]]:
        """Return whether update notifications should be sent and why.

        Rules:
        - send on start/end time changes
        - send on location change
        - send when event becomes archived (`is_active: true -> false`)
        """
        reasons: list[str] = []
        if not self._datetime_equal(old_event.starts_at, new_event.starts_at):
            reasons.append("start_time")
        if not self._datetime_equal(old_event.ends_at, new_event.ends_at):
            reasons.append("end_time")
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
        notification_type: NotificationType = NotificationType.EVENT_UPDATE,
    ) -> list[NotificationRecipient]:
        logger.info(
            "Resolving recipients for event=%s notification_type=%s exclude_user_id=%s",
            event_id,
            notification_type.value,
            exclude_user_id,
        )
        membership_response = (
            self.admin_client.table("event_memberships")
            .select("user_id")
            .eq("event_id", str(event_id))
            .execute()
        )
        user_ids: list[UUID] = []
        rows = membership_response.data or []
        logger.info(
            "Fetched %s membership rows for event=%s notification_type=%s",
            len(rows),
            event_id,
            notification_type.value,
        )
        for row in rows:
            if not isinstance(row, Mapping):
                continue
            row_dict = row
            user_id_raw = row_dict.get("user_id")
            if isinstance(user_id_raw, str):
                user_ids.append(UUID(user_id_raw))
        logger.info(
            "Parsed %s user ids for event=%s before exclusion notification_type=%s",
            len(user_ids),
            event_id,
            notification_type.value,
        )
        if exclude_user_id:
            user_ids = [user_id for user_id in user_ids if user_id != exclude_user_id]
            logger.info(
                (
                    "Recipient candidates reduced to %s after excluding user=%s "
                    "for event=%s notification_type=%s"
                ),
                len(user_ids),
                exclude_user_id,
                event_id,
                notification_type.value,
            )
        if not user_ids:
            logger.warning(
                "No recipient candidates found for event=%s notification_type=%s after exclusion",
                event_id,
                notification_type.value,
            )
            return []

        opted_in_user_ids = set(
            await self._filter_opted_in_user_ids(
                user_ids=user_ids,
                notification_type=notification_type,
            )
        )
        logger.info(
            "Opt-in filter kept %s of %s users for event=%s notification_type=%s",
            len(opted_in_user_ids),
            len(user_ids),
            event_id,
            notification_type.value,
        )
        if not opted_in_user_ids:
            logger.warning(
                "All recipient candidates opted out for event=%s notification_type=%s",
                event_id,
                notification_type.value,
            )
            return []

        recipients: list[NotificationRecipient] = []
        for user_id in user_ids:
            if user_id not in opted_in_user_ids:
                continue
            email = self._get_user_email(user_id)
            if not email:
                logger.warning(
                    (
                        "Skipping recipient user=%s for event=%s notification_type=%s "
                        "because no email was found"
                    ),
                    user_id,
                    event_id,
                    notification_type.value,
                )
                continue
            recipients.append(NotificationRecipient(user_id=user_id, email=email))
        logger.info(
            "Resolved %s deliverable recipients for event=%s notification_type=%s",
            len(recipients),
            event_id,
            notification_type.value,
        )
        return recipients

    async def _filter_opted_in_user_ids(
        self,
        *,
        user_ids: list[UUID],
        notification_type: NotificationType,
    ) -> list[UUID]:
        """Keep users opted in for the requested notification type.

        Missing preference rows default to opted-in behavior.
        """
        if not user_ids:
            return []

        try:
            if notification_type == NotificationType.HOST_MESSAGE:
                return list(await self.notification_dal.get_host_message_opt_in_user_ids(user_ids))
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
        logger.info(
            (
                "Beginning notification send for event=%s notification_type=%s "
                "recipient_count=%s subject=%r"
            ),
            event_id,
            notification_type.value,
            len(recipients),
            subject,
        )
        for recipient in recipients:
            logger.info(
                "Attempting notification send to user=%s email=%s event=%s type=%s",
                recipient.user_id,
                recipient.email,
                event_id,
                notification_type.value,
            )
            sent = await self._send_email(
                recipient_email=recipient.email, subject=subject, body=body
            )
            if sent:
                logger.info(
                    "Notification email sent to user=%s email=%s type=%s event=%s",
                    recipient.user_id,
                    recipient.email,
                    notification_type.value,
                    event_id,
                )
            else:
                logger.warning(
                    (
                        "Notification email send reported failure for "
                        "user=%s email=%s type=%s event=%s"
                    ),
                    recipient.user_id,
                    recipient.email,
                    notification_type.value,
                    event_id,
                )
            await self._log_notification(
                user_id=recipient.user_id,
                event_id=event_id,
                notification_type=notification_type,
                status=NotificationStatus.SENT if sent else NotificationStatus.FAILED,
            )

    async def _send_email(self, *, recipient_email: str, subject: str, body: str) -> bool:
        if not self.settings.mail_enabled:
            logger.warning(
                "Mail disabled; skipping notification email to %s with subject=%r",
                recipient_email,
                subject,
            )
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
        context: dict[str, str | bool] = {
            "event_name": new_event.name,
            "show_start_time": "start_time" in reasons,
            "show_end_time": "end_time" in reasons,
            "from_start_time": self._format_datetime_or_tbd(old_event.starts_at),
            "to_start_time": self._format_datetime_or_tbd(new_event.starts_at),
            "from_end_time": self._format_datetime_or_tbd(old_event.ends_at),
            "to_end_time": self._format_datetime_or_tbd(new_event.ends_at),
            "show_location": "location" in reasons,
            "from_location": old_event.location or "TBD",
            "to_location": new_event.location or "TBD",
            "archived": "archived" in reasons,
            "cta_url": self._build_dashboard_url(event_id=new_event.event_id),
            "app_name": _APP_BRAND_NAME,
        }
        return self._render_email_template("event_update.html", context)

    def _build_deleted_email_body(self, event: EventResponse) -> str:
        context: dict[str, str] = {
            "event_name": event.name,
            "scheduled_time": self._format_time(event.starts_at, event.ends_at),
            "location": event.location or "TBD",
            "cta_url": self._build_dashboard_url(event_id=None),
            "app_name": _APP_BRAND_NAME,
        }
        return self._render_email_template("event_deleted.html", context)

    def _build_host_message_email_body(
        self,
        *,
        event: EventResponse,
        message: str,
    ) -> str:
        paragraphs = [line.strip() for line in message.splitlines() if line.strip()]
        context: dict[str, object] = {
            "event_name": event.name,
            "scheduled_time": self._format_time(event.starts_at, event.ends_at),
            "location": event.location or "TBD",
            "message_paragraphs": paragraphs or [message.strip()],
            "cta_url": self._build_dashboard_url(event_id=event.event_id),
            "app_name": _APP_BRAND_NAME,
        }
        return self._render_email_template("host_message.html", context)

    @staticmethod
    def _format_time(starts_at: datetime | None, ends_at: datetime | None) -> str:
        if starts_at is None and ends_at is None:
            return "TBD"
        if starts_at and ends_at:
            return (
                f"{NotificationService._format_datetime(starts_at)} to "
                f"{NotificationService._format_datetime(ends_at)}"
            )
        if starts_at:
            return f"Starts {NotificationService._format_datetime(starts_at)}"
        if ends_at:
            return f"Ends {NotificationService._format_datetime(ends_at)}"
        return "TBD"

    @staticmethod
    def _format_datetime_or_tbd(value: datetime | None) -> str:
        if value is None:
            return "TBD"
        return NotificationService._format_datetime(value)

    @staticmethod
    def _format_datetime(value: datetime) -> str:
        """Format a datetime for end-user email readability."""
        dt = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        dt_eastern = dt.astimezone(_EASTERN_TZ)
        hour = dt_eastern.strftime("%I").lstrip("0") or "12"
        return (
            f"{dt_eastern.strftime('%a')}, {dt_eastern.strftime('%b')} {dt_eastern.day}, "
            f"{dt_eastern.year} at {hour}:{dt_eastern.strftime('%M')} "
            f"{dt_eastern.strftime('%p')} {dt_eastern.strftime('%Z')}"
        )

    @staticmethod
    def _render_email_template(template_name: str, context: Mapping[str, object]) -> str:
        template = _EMAIL_TEMPLATE_ENV.get_template(template_name)
        return template.render(**context)

    def _build_dashboard_url(self, *, event_id: UUID | None) -> str:
        base_url = self.settings.frontend_app_url.rstrip("/")
        if not event_id:
            return f"{base_url}/dashboard"
        query = urlencode({"event_id": str(event_id)})
        return f"{base_url}/dashboard?{query}"
