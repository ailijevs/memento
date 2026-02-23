"""S3 helpers for uploading user assets."""

from __future__ import annotations

from io import BytesIO
from typing import Any, BinaryIO, Literal
from uuid import UUID

from dotenv import load_dotenv

load_dotenv()

ProfilePhotoSource = Literal["onboarding", "linkedin"]

_DEFAULT_EXTENSION = ".jpg"
_DEFAULT_CONTENT_TYPE = "image/jpeg"


def normalize_image_stream_to_jpeg(
    image: bytes | BinaryIO,
    *,
    quality: int = 90,
) -> bytes:
    """Normalize an image byte stream to JPEG bytes.

    Args:
        image: Raw image bytes or a readable binary stream.
        quality: JPEG quality (1-95).

    Returns:
        JPEG-encoded image bytes.

    Raises:
        ValueError: If input image is empty or quality is out of range.
        RuntimeError: If Pillow is unavailable.
    """
    if not 1 <= quality <= 95:
        raise ValueError("quality must be between 1 and 95.")

    image_bytes = _read_image_bytes(image)
    if not image_bytes:
        raise ValueError("image must not be empty.")

    try:
        from PIL import Image, ImageOps
    except ImportError as exc:  # pragma: no cover - depends on optional dependency.
        raise RuntimeError(
            "Pillow is required to normalize images. Install pillow to use this function."
        ) from exc

    with Image.open(BytesIO(image_bytes)) as original_image:
        processed_image = ImageOps.exif_transpose(original_image)
        rgb_image = _to_rgb(processed_image)

        output = BytesIO()
        rgb_image.save(output, format="JPEG", quality=quality, optimize=True)
        return output.getvalue()


def upload_profile_picture(
    *,
    user_id: UUID | str,
    image: bytes | BinaryIO,
    bucket_name: str,
    source: ProfilePhotoSource,
    s3_client: Any | None = None,
) -> str:
    """Upload a user's profile picture to S3 as JPEG and return the stored object key.

    Args:
        user_id: User identifier used to namespace the uploaded object.
        image: Image bytes or a readable binary stream.
        bucket_name: Destination S3 bucket name.
        source: Origin of the image ("onboarding" or "linkedin").
        s3_client: Optional injected boto3 S3 client for easier testing.

    Returns:
        The S3 object key suitable for persisting in `photo_path`.
        All uploads are normalized to JPEG with `.jpg` extension.

    Raises:
        ValueError: If bucket name is blank or image is empty.
        RuntimeError: If boto3 is unavailable and no client is injected.
    """
    cleaned_bucket_name = bucket_name.strip()
    if not cleaned_bucket_name:
        raise ValueError("bucket_name must not be empty.")

    image_bytes = _read_image_bytes(image)
    if not image_bytes:
        raise ValueError("image must not be empty.")

    normalized_image = normalize_image_stream_to_jpeg(image_bytes)
    object_key = f"profiles/{user_id}-{source}{_DEFAULT_EXTENSION}"

    client = s3_client or _create_s3_client()
    client.upload_fileobj(
        BytesIO(normalized_image),
        cleaned_bucket_name,
        object_key,
        ExtraArgs={"ContentType": _DEFAULT_CONTENT_TYPE},
    )
    return object_key


def delete_profile_picture(
    *,
    s3_key: str,
    bucket_name: str,
    s3_client: Any | None = None,
) -> None:
    """Delete a profile picture object from S3.

    Args:
        s3_key: Object key stored in `photo_path`.
        bucket_name: Source S3 bucket name.
        s3_client: Optional injected boto3 S3 client for easier testing.

    Raises:
        ValueError: If bucket name or key is blank.
        RuntimeError: If boto3 is unavailable and no client is injected.
    """
    cleaned_bucket_name = bucket_name.strip()
    if not cleaned_bucket_name:
        raise ValueError("bucket_name must not be empty.")

    cleaned_s3_key = s3_key.strip()
    if not cleaned_s3_key:
        raise ValueError("s3_key must not be empty.")

    client = s3_client or _create_s3_client()
    client.delete_object(Bucket=cleaned_bucket_name, Key=cleaned_s3_key)


def _read_image_bytes(image: bytes | BinaryIO) -> bytes:
    """Read bytes from either raw bytes or a binary stream."""
    if isinstance(image, bytes):
        return image
    return image.read()


def _create_s3_client() -> Any:
    """Create a boto3 S3 client when one is not injected."""
    try:
        import boto3
    except ImportError as exc:  # pragma: no cover - depends on optional dependency.
        raise RuntimeError(
            "boto3 is required to upload profile pictures. "
            "Install boto3 or inject an initialized s3_client."
        ) from exc

    return boto3.client("s3")


def _to_rgb(image: Any) -> Any:
    """Convert a Pillow image to RGB, flattening alpha onto white if needed."""
    from PIL import Image

    if image.mode in {"RGBA", "LA"}:
        background = image.getchannel("A")
        converted = Image.new("RGB", image.size, (255, 255, 255))
        converted.paste(image.convert("RGB"), mask=background)
        return converted

    if image.mode != "RGB":
        return image.convert("RGB")

    return image


if __name__ == "__main__":
    from app.config import get_settings

    settings = get_settings()
    if not settings.s3_bucket_name:
        raise RuntimeError("s3_bucket_name is not configured in environment settings.")

    # Uncomment to delete the profile picture.
    # object_key = "profiles/ab87fdd7-6941-48c9-904f-d60fdeaa55f5-onboarding.jpg"
    # delete_profile_picture(s3_key=object_key, bucket_name=settings.s3_bucket_name)
    # print(f"Deleted profile picture: {object_key}")

    # Uncomment to upload the same profile picture key back to S3.
    from pathlib import Path

    image_path = Path(__file__).resolve().parents[2] / "data/profile_images/nmgbodil.jpg"
    with image_path.open("rb") as image_file:
        restored_key = upload_profile_picture(
            user_id="ab87fdd7-6941-48c9-904f-d60fdeaa55f5",
            image=image_file,
            bucket_name=settings.s3_bucket_name,
            source="onboarding",
        )
    print(f"Re-uploaded profile picture: {restored_key}")
