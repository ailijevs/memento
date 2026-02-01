"""Base Data Access Layer with common functionality."""

from supabase import Client


class BaseDAL:
    """Base class for all DALs providing common Supabase client access."""

    def __init__(self, client: Client):
        """
        Initialize DAL with Supabase client.

        Args:
            client: Supabase client instance (should have user's JWT for RLS).
        """
        self.client = client
