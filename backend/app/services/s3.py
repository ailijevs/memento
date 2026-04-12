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


class S3Service:
    """Service wrapper around an S3 client."""

    def __init__(self, s3_client: Any | None = None) -> None:
        self.client = s3_client or self._create_client()

    def normalize_image_stream_to_jpeg(
        self,
        image: bytes | BinaryIO,
        *,
        quality: int = 90,
    ) -> bytes:
        """Normalize an image byte stream to JPEG bytes."""
        if not 1 <= quality <= 95:
            raise ValueError("quality must be between 1 and 95.")

        image_bytes = self._read_image_bytes(image)
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
            rgb_image = self._to_rgb(processed_image)

            output = BytesIO()
            rgb_image.save(output, format="JPEG", quality=quality, optimize=True)
            return output.getvalue()

    def upload_profile_picture(
        self,
        *,
        user_id: UUID | str,
        image: bytes | BinaryIO,
        bucket_name: str,
        source: ProfilePhotoSource,
    ) -> str:
        """Upload a user's profile picture to S3 as JPEG and return object key."""
        cleaned_bucket_name = self._clean_bucket_name(bucket_name)

        image_bytes = self._read_image_bytes(image)
        if not image_bytes:
            raise ValueError("image must not be empty.")

        normalized_image = self.normalize_image_stream_to_jpeg(image_bytes)
        object_key = self._build_profile_picture_key(user_id=user_id, source=source)

        self.client.upload_fileobj(
            BytesIO(normalized_image),
            cleaned_bucket_name,
            object_key,
            ExtraArgs={"ContentType": _DEFAULT_CONTENT_TYPE},
        )
        return object_key

    def generate_upload_url(
        self,
        *,
        user_id: UUID | str,
        bucket_name: str,
        source: ProfilePhotoSource,
        expires_in_seconds: int = 600,
        content_type: str = _DEFAULT_CONTENT_TYPE,
    ) -> dict[str, str]:
        """Create a pre-signed PUT URL for uploading a profile picture directly to S3."""
        cleaned_bucket_name = self._clean_bucket_name(bucket_name)
        cleaned_content_type = content_type.strip()
        if not cleaned_content_type:
            raise ValueError("content_type must not be empty.")
        if expires_in_seconds <= 0:
            raise ValueError("expires_in_seconds must be greater than 0.")

        object_key = self._build_profile_picture_key(
            user_id=user_id,
            source=source,
            include_extension=False,
        )
        try:
            upload_url = self.client.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": cleaned_bucket_name,
                    "Key": object_key,
                    "ContentType": cleaned_content_type,
                },
                ExpiresIn=expires_in_seconds,
            )
        except Exception as exc:
            raise RuntimeError(
                f"Failed to generate upload URL for profile key '{object_key}'."
            ) from exc

        return {
            "upload_url": upload_url,
            "s3_key": object_key,
            "content_type": cleaned_content_type,
        }

    def delete_profile_picture(
        self,
        *,
        s3_key: str,
        bucket_name: str,
    ) -> None:
        """Delete a profile picture object from S3."""
        cleaned_bucket_name = self._clean_bucket_name(bucket_name)
        cleaned_s3_key = self._clean_s3_key(s3_key)

        self.client.delete_object(Bucket=cleaned_bucket_name, Key=cleaned_s3_key)

    def get_profile_picture_presigned_url(
        self,
        *,
        s3_key: str,
        bucket_name: str,
        expires_in_seconds: int = 3600,
    ) -> Any:
        """Return a pre-signed URL for a profile picture object."""
        cleaned_bucket_name = self._clean_bucket_name(bucket_name)

        if expires_in_seconds <= 0:
            raise ValueError("expires_in_seconds must be greater than 0.")

        cleaned_s3_key = self._clean_s3_key(s3_key)

        try:
            return self.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": cleaned_bucket_name, "Key": cleaned_s3_key},
                ExpiresIn=expires_in_seconds,
            )
        except Exception as exc:
            raise RuntimeError(
                f"Failed to generate pre-signed URL for profile key '{cleaned_s3_key}'."
            ) from exc

    def profile_picture_exists(
        self,
        *,
        s3_key: str,
        bucket_name: str,
    ) -> bool:
        """Return True if a profile picture object exists in S3."""
        cleaned_bucket_name = self._clean_bucket_name(bucket_name)
        cleaned_s3_key = self._clean_s3_key(s3_key)

        try:
            self.client.head_object(Bucket=cleaned_bucket_name, Key=cleaned_s3_key)
            return True
        except Exception as exc:
            if self._is_not_found_error(exc):
                return False
            raise RuntimeError(
                f"Failed to verify existence for profile key '{cleaned_s3_key}'."
            ) from exc

    def is_not_found_error(self, exc: Exception) -> bool:
        """Return True when an S3 exception indicates object/key not found."""
        return self._is_not_found_error(exc)

    def _create_client(self) -> Any:
        """Create a boto3 S3 client when one is not injected."""
        try:
            import boto3
        except ImportError as exc:  # pragma: no cover - depends on optional dependency.
            raise RuntimeError(
                "boto3 is required to upload profile pictures. "
                "Install boto3 or inject an initialized s3_client."
            ) from exc

        return boto3.client("s3")

    def _read_image_bytes(self, image: bytes | BinaryIO) -> bytes:
        """Read bytes from either raw bytes or a binary stream."""
        if isinstance(image, bytes):
            return image
        return image.read()

    def _clean_bucket_name(self, bucket_name: str) -> str:
        """Return normalized bucket name or raise if empty."""
        cleaned_bucket_name = bucket_name.strip()
        if not cleaned_bucket_name:
            raise ValueError("bucket_name must not be empty.")
        return cleaned_bucket_name

    def _clean_s3_key(self, s3_key: str) -> str:
        """Return normalized S3 object key or raise if empty."""
        cleaned_s3_key = s3_key.strip()
        if not cleaned_s3_key:
            raise ValueError("s3_key must not be empty.")
        return cleaned_s3_key

    def _build_profile_picture_key(
        self,
        *,
        user_id: UUID | str,
        source: ProfilePhotoSource,
        include_extension: bool = True,
    ) -> str:
        """Build canonical profile picture object key."""
        cleaned_user_id = str(user_id).strip()
        if not cleaned_user_id:
            raise ValueError("user_id must not be empty.")
        key = f"profiles/{cleaned_user_id}-{source}"
        if include_extension:
            key += _DEFAULT_EXTENSION
        return key

    def _is_not_found_error(self, exc: Exception) -> bool:
        """Return True when an S3 exception indicates the object does not exist."""
        message = str(exc)
        if "NoSuchKey" in message or "NoSuchObject" in message:
            return True
        response = getattr(exc, "response", None)
        if isinstance(response, dict):
            error = response.get("Error", {})
            code = str(error.get("Code", ""))
            return code in {"NoSuchKey", "NoSuchObject", "404", "NotFound"}
        return False

    def _to_rgb(self, image: Any) -> Any:
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

    s3_service = S3Service()

    # Uncomment to delete the profile picture.
    # object_key = "profiles/ab87fdd7-6941-48c9-904f-d60fdeaa55f5-onboarding.jpg"
    # s3_service.delete_profile_picture(s3_key=object_key, bucket_name=settings.s3_bucket_name)
    # print(f"Deleted profile picture: {object_key}")

    # Uncomment to upload the same profile picture key back to S3.
    from pathlib import Path

    image_path = Path(__file__).resolve().parents[2] / "data/profile_images/nmgbodil.jpg"
    with image_path.open("rb") as image_file:
        restored_key = s3_service.upload_profile_picture(
            user_id="ab87fdd7-6941-48c9-904f-d60fdeaa55f5",
            image=image_file,
            bucket_name=settings.s3_bucket_name,
            source="onboarding",
        )
    print(f"Re-uploaded profile picture: {restored_key}")
