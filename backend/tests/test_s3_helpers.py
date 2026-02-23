"""Tests for shared S3 helper functions."""

from io import BytesIO
from typing import Any

from PIL import Image

from app.utils.s3_helpers import normalize_image_stream_to_jpeg, upload_profile_picture


class FakeS3Client:
    """Simple stub client for verifying upload args."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def upload_fileobj(
        self,
        fileobj: Any,
        bucket: str,
        key: str,
        ExtraArgs: dict[str, str] | None = None,  # noqa: N803
    ) -> None:
        self.calls.append(
            {
                "body": fileobj.read(),
                "bucket": bucket,
                "key": key,
                "extra": ExtraArgs or {},
            }
        )


def test_normalize_image_stream_to_jpeg_returns_jpeg_bytes():
    """PNG bytes should normalize to JPEG bytes."""
    img = Image.new("RGB", (8, 8), color="red")
    png = BytesIO()
    img.save(png, format="PNG")

    jpeg_bytes = normalize_image_stream_to_jpeg(png.getvalue())

    assert jpeg_bytes[:3] == b"\xff\xd8\xff"
    assert len(jpeg_bytes) > 10


def test_upload_profile_picture_uses_stream_and_returns_object_key():
    """Upload should send JPEG stream to S3 and return stored key."""
    img = Image.new("RGB", (8, 8), color="blue")
    png = BytesIO()
    img.save(png, format="PNG")

    fake = FakeS3Client()
    key = upload_profile_picture(
        user_id="1234",
        image=png.getvalue(),
        bucket_name="memento-profile-pictures",
        source="linkedin",
        s3_client=fake,
    )

    assert key == "profile_images/1234-linkedin.jpg"
    assert len(fake.calls) == 1
    assert fake.calls[0]["bucket"] == "memento-profile-pictures"
    assert fake.calls[0]["extra"]["ContentType"] == "image/jpeg"
    assert fake.calls[0]["body"][:3] == b"\xff\xd8\xff"
