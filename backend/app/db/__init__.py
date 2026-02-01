"""Database module for Supabase client initialization."""

from .supabase import get_admin_client, get_supabase_client

__all__ = ["get_admin_client", "get_supabase_client"]
