"""
Application configuration using pydantic-settings.
Environment variables are loaded from .env file.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Supabase Configuration
    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str  # For admin operations (use sparingly)
    supabase_jwt_secret: str  # For verifying JWTs

    # Application Settings
    app_name: str = "Memento API"
    app_version: str = "0.0.0-dev"
    debug: bool = False

    # External APIs (optional)
    exa_api_key: str | None = None
    mentra_api_key: str | None = None
    mentra_api_key_hash: str | None = None
    web_api_key_hash: str | None = None
    pdl_api_key: str | None = None
    openai_api_key: str | None = None
    profile_summary_provider: str = "auto"  # auto | dspy | template
    profile_summary_model: str = "openai/gpt-4o-mini"
    # Service-to-service auth for recognition endpoints (e.g., Mentra cloud app)
    recognition_service_token: str | None = None

    # AWS/S3 Configuration
    aws_region: str = "us-east-2"
    s3_bucket_name: str | None = None
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None

    @property
    def hash_to_client(self) -> dict[str, str]:
        """Map known API key hashes to client identifiers."""
        mapping: dict[str, str] = {}
        if self.mentra_api_key_hash:
            mapping[self.mentra_api_key_hash] = "mentra"
        if self.web_api_key_hash:
            mapping[self.web_api_key_hash] = "web_frontend"
        return mapping


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()  # type: ignore[call-arg]
