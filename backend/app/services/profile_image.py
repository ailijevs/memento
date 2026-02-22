"""Profile image download and JPEG normalization utilities."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from uuid import UUID

import httpx


class ProfileImageError(Exception):
    """Raised when profile image processing fails."""


class ProfileImageService:
    """Download profile images and save a normalized JPEG copy."""

    def __init__(self) -> None:
        self.output_dir = Path(__file__).resolve().parents[2] / "data" / "profile_images"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def save_profile_image_as_jpeg(self, image_url: str, user_id: UUID) -> str:
        """Download image from URL, convert to JPEG, and return relative storage path."""
        if not image_url:
            raise ProfileImageError("Missing image URL.")

        async with httpx.AsyncClient(timeout=25.0, follow_redirects=True) as client:
            response = await client.get(image_url)

        if response.status_code >= 400:
            raise ProfileImageError(f"Failed to download image ({response.status_code}).")

        output_name = f"{user_id}.jpg"
        output_path = self.output_dir / output_name

        try:
            from PIL import Image

            img = Image.open(BytesIO(response.content))
            rgb = img.convert("RGB")
            rgb.save(output_path, format="JPEG", quality=90)
        except ImportError as exc:
            raise ProfileImageError("Pillow is required for image conversion. Install pillow.") from exc
        except Exception as exc:  # noqa: BLE001
            raise ProfileImageError(f"Failed to convert image to JPEG: {exc}") from exc

        return f"profile_images/{output_name}"
