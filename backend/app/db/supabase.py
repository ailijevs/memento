"""
Supabase client initialization and dependency injection.
"""
from functools import lru_cache
from supabase import create_client, Client

from app.config import get_settings


@lru_cache
def get_admin_client() -> Client:
    """
    Get Supabase client with service role key.
    Use sparingly - bypasses RLS.
    """
    settings = get_settings()
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


def get_supabase_client(access_token: str | None = None) -> Client:
    """
    Get Supabase client with anon key.
    If access_token is provided, it sets the auth header for RLS.
    """
    settings = get_settings()
    client = create_client(settings.supabase_url, settings.supabase_anon_key)

    if access_token:
        # Set the user's JWT for RLS enforcement
        client.postgrest.auth(access_token)

    return client
