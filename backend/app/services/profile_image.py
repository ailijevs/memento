"""Profile image download utilities."""

from __future__ import annotations

import httpx


class ProfileImageError(Exception):
    """Raised when profile image processing fails."""


class ProfileImageService:
    """Download profile images as raw bytes."""

    async def fetch_image_bytes(self, image_url: str) -> bytes:
        """Download image from URL and return raw image bytes."""
        if not image_url:
            raise ProfileImageError("Missing image URL.")

        async with httpx.AsyncClient(timeout=25.0, follow_redirects=True) as client:
            response = await client.get(image_url)

        if response.status_code >= 400:
            raise ProfileImageError(f"Failed to download image ({response.status_code}).")

        return response.content
