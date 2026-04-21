"""Email delivery service backed by FastAPI Mail."""

from __future__ import annotations

from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from pydantic import NameEmail, SecretStr

from app.config import Settings, get_settings


class EmailConfigurationError(RuntimeError):
    """Raised when email settings are missing or invalid."""


class EmailService:
    """Thin wrapper around FastAPI Mail for SMTP email delivery."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

    @property
    def enabled(self) -> bool:
        """Whether outbound email is enabled by configuration."""
        return self.settings.mail_enabled

    def _require_config(self) -> ConnectionConfig:
        if not self.enabled:
            raise EmailConfigurationError("Email sending is disabled. Set MAIL_ENABLED=true.")

        required_values = {
            "MAIL_FROM": self.settings.mail_from,
            "MAIL_USERNAME": self.settings.mail_username,
            "MAIL_PASSWORD": self.settings.mail_password,
        }
        missing = [name for name, value in required_values.items() if not value]
        if missing:
            joined = ", ".join(missing)
            raise EmailConfigurationError(
                f"Email sending is enabled, but required env vars are missing: {joined}"
            )

        # Values are guaranteed non-null after the missing check above.
        mail_username = self.settings.mail_username
        mail_password = self.settings.mail_password
        mail_from = self.settings.mail_from
        if mail_username is None or mail_password is None or mail_from is None:
            raise EmailConfigurationError("Email settings are invalid.")

        return ConnectionConfig(
            MAIL_USERNAME=mail_username,
            MAIL_PASSWORD=SecretStr(mail_password),
            MAIL_FROM=mail_from,
            MAIL_FROM_NAME=self.settings.mail_from_name,
            MAIL_SERVER=self.settings.mail_server,
            MAIL_PORT=self.settings.mail_port,
            MAIL_STARTTLS=self.settings.mail_starttls,
            MAIL_SSL_TLS=self.settings.mail_ssl_tls,
            USE_CREDENTIALS=True,
            VALIDATE_CERTS=self.settings.mail_validate_certs,
        )

    async def send_email(
        self,
        *,
        recipients: list[str],
        subject: str,
        body: str,
        is_html: bool = True,
    ) -> None:
        """Send an email to one or more recipients."""
        if not recipients:
            raise ValueError("At least one recipient email is required.")

        config = self._require_config()
        name_email_recipients = [
            NameEmail(name=recipient.split("@")[0], email=recipient) for recipient in recipients
        ]
        message = MessageSchema(
            recipients=name_email_recipients,
            subject=subject,
            body=body,
            subtype=MessageType.html if is_html else MessageType.plain,
        )
        fm = FastMail(config)
        await fm.send_message(message)


def get_email_service() -> EmailService:
    """Factory for dependency injection and direct usage."""
    return EmailService()
