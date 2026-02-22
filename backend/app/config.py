"""
Application configuration using pydantic-settings.
Environment variables are loaded from .env file.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Supabase Configuration
    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str  # For admin operations (use sparingly)
    supabase_jwt_secret: str  # For verifying JWTs

    # Application Settings
    app_name: str = "Memento API"
    debug: bool = False

    # External APIs (optional)
    exa_api_key: str | None = None
    mentra_api_key: str | None = None

    # AWS/S3 Configuration
    aws_region: str = "us-east-2"
    s3_bucket_name: str | None = None
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()  # type: ignore[call-arg]
