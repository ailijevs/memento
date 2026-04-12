"""Tests for app.services.s3."""

from __future__ import annotations

import builtins
import importlib
import sys
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

_ROOT = str(Path(__file__).resolve().parents[3])
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
s3 = importlib.import_module("app.services.s3")
S3Service = s3.S3Service


class DummyS3Client:
    """Capture upload inputs for assertions."""

    def __init__(self) -> None:
        self.calls: list[dict] = []
        self.delete_calls: list[dict] = []
        self.presign_calls: list[dict] = []
        self.head_calls: list[dict] = []
        self.presign_url = "https://example.com/presigned"
        self.head_exception: Exception | None = None

    def upload_fileobj(self, fileobj, bucket, key, ExtraArgs):  # noqa: N803
        """Record upload details from boto3-compatible upload call."""
        self.calls.append(
            {
                "bytes": fileobj.read(),
                "bucket": bucket,
                "key": key,
                "extra_args": ExtraArgs,
            }
        )

    def delete_object(self, Bucket, Key):  # noqa: N803
        """Record delete details from boto3-compatible delete call."""
        self.delete_calls.append({"bucket": Bucket, "key": Key})

    def generate_presigned_url(self, ClientMethod, Params, ExpiresIn):  # noqa: N803
        """Record presign details from boto3-compatible presign call."""
        self.presign_calls.append(
            {"client_method": ClientMethod, "params": Params, "expires_in": ExpiresIn}
        )
        return self.presign_url

    def head_object(self, Bucket, Key):  # noqa: N803
        """Record head_object checks or raise a configured exception."""
        self.head_calls.append({"bucket": Bucket, "key": Key})
        if self.head_exception is not None:
            raise self.head_exception
        return {"ResponseMetadata": {"HTTPStatusCode": 200}}


def _png_bytes(mode: str = "RGB") -> bytes:
    pytest.importorskip("PIL")
    from PIL import Image

    image = Image.new(mode, (3, 3), (10, 20, 30, 255) if "A" in mode else (10, 20, 30))
    out = BytesIO()
    image.save(out, format="PNG")
    return out.getvalue()


def test_read_image_bytes_supports_raw_bytes_and_streams():
    """_read_image_bytes returns bytes for both bytes and stream inputs."""
    service = S3Service(s3_client=DummyS3Client())
    assert service._read_image_bytes(b"abc") == b"abc"
    assert service._read_image_bytes(BytesIO(b"def")) == b"def"


def test_normalize_image_stream_to_jpeg_returns_jpeg_bytes():
    """normalize_image_stream_to_jpeg returns JPEG-encoded bytes."""
    service = S3Service(s3_client=DummyS3Client())
    result = service.normalize_image_stream_to_jpeg(_png_bytes())
    assert result[:2] == b"\xff\xd8"
    assert len(result) > 10


def test_normalize_image_stream_to_jpeg_accepts_stream_input():
    """normalize_image_stream_to_jpeg accepts binary stream input."""
    service = S3Service(s3_client=DummyS3Client())
    result = service.normalize_image_stream_to_jpeg(BytesIO(_png_bytes()))
    assert result[:2] == b"\xff\xd8"


@pytest.mark.parametrize("quality", [0, 96])
def test_normalize_image_stream_to_jpeg_rejects_invalid_quality(quality):
    """normalize_image_stream_to_jpeg rejects out-of-range quality."""
    service = S3Service(s3_client=DummyS3Client())
    with pytest.raises(ValueError, match="quality must be between 1 and 95"):
        service.normalize_image_stream_to_jpeg(_png_bytes(), quality=quality)


@pytest.mark.parametrize("payload", [b"", BytesIO(b"")])
def test_normalize_image_stream_to_jpeg_rejects_empty_images(payload):
    """normalize_image_stream_to_jpeg rejects empty payloads."""
    service = S3Service(s3_client=DummyS3Client())
    with pytest.raises(ValueError, match="image must not be empty"):
        service.normalize_image_stream_to_jpeg(payload)


def test_normalize_image_stream_to_jpeg_raises_when_pillow_missing(monkeypatch):
    """normalize_image_stream_to_jpeg raises runtime error when PIL is unavailable."""
    real_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "PIL":
            raise ImportError("No module named PIL")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    service = S3Service(s3_client=DummyS3Client())
    with pytest.raises(RuntimeError, match="Pillow is required to normalize images"):
        service.normalize_image_stream_to_jpeg(b"not-empty")


def test_to_rgb_returns_rgb_for_rgba():
    """_to_rgb flattens RGBA input into RGB."""
    pytest.importorskip("PIL")
    from PIL import Image

    rgba = Image.new("RGBA", (2, 2), (40, 50, 60, 120))
    service = S3Service(s3_client=DummyS3Client())
    converted = service._to_rgb(rgba)
    assert converted.mode == "RGB"


def test_to_rgb_converts_non_rgb_modes():
    """_to_rgb converts non-RGB modes to RGB."""
    pytest.importorskip("PIL")
    from PIL import Image

    grayscale = Image.new("L", (2, 2), 200)
    service = S3Service(s3_client=DummyS3Client())
    converted = service._to_rgb(grayscale)
    assert converted.mode == "RGB"


def test_to_rgb_returns_original_rgb_image():
    """_to_rgb returns original object when already RGB."""
    pytest.importorskip("PIL")
    from PIL import Image

    rgb = Image.new("RGB", (2, 2), (1, 2, 3))
    service = S3Service(s3_client=DummyS3Client())
    converted = service._to_rgb(rgb)
    assert converted is rgb


def test_create_s3_client_constructs_boto3_client(monkeypatch):
    """_create_s3_client delegates to boto3.client('s3')."""
    calls = []
    fake_client = object()
    fake_boto3 = SimpleNamespace(
        client=lambda service_name: calls.append(service_name) or fake_client
    )
    monkeypatch.setitem(sys.modules, "boto3", fake_boto3)

    service = S3Service.__new__(S3Service)
    created = service._create_client()
    assert created is fake_client
    assert calls == ["s3"]


def test_create_s3_client_raises_when_boto3_missing(monkeypatch):
    """_create_s3_client raises runtime error when boto3 is unavailable."""
    real_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "boto3":
            raise ImportError("No module named boto3")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    service = S3Service.__new__(S3Service)
    with pytest.raises(RuntimeError, match="boto3 is required to upload profile pictures"):
        service._create_client()


def test_upload_profile_picture_validates_inputs(monkeypatch):
    """upload_profile_picture validates bucket and image payload."""
    service = S3Service(s3_client=DummyS3Client())
    monkeypatch.setattr(service, "normalize_image_stream_to_jpeg", lambda image: image)
    with pytest.raises(ValueError, match="bucket_name must not be empty"):
        service.upload_profile_picture(
            user_id="u1",
            image=b"payload",
            bucket_name="   ",
            source="onboarding",
        )
    with pytest.raises(ValueError, match="image must not be empty"):
        service.upload_profile_picture(
            user_id="u1",
            image=b"",
            bucket_name="bucket",
            source="onboarding",
        )


def test_upload_profile_picture_normalizes_and_uploads_with_expected_metadata(monkeypatch):
    """upload_profile_picture uploads normalized JPEG with expected metadata."""
    client = DummyS3Client()
    observed = {}

    def fake_normalize(image: bytes) -> bytes:
        observed["input"] = image
        return b"jpeg-bytes"

    service = S3Service(s3_client=client)
    monkeypatch.setattr(service, "normalize_image_stream_to_jpeg", fake_normalize)

    user_id = str(uuid4())
    object_key = service.upload_profile_picture(
        user_id=user_id,
        image=BytesIO(b"original-image"),
        bucket_name=" my-bucket ",
        source="linkedin",
    )

    assert observed["input"] == b"original-image"
    assert object_key == f"profiles/{user_id}-linkedin.jpg"
    assert len(client.calls) == 1
    assert client.calls[0]["bytes"] == b"jpeg-bytes"
    assert client.calls[0]["bucket"] == "my-bucket"
    assert client.calls[0]["key"] == f"profiles/{user_id}-linkedin.jpg"
    assert client.calls[0]["extra_args"] == {"ContentType": "image/jpeg"}


def test_upload_profile_picture_uses_default_client(monkeypatch):
    """upload_profile_picture uses default client when no client is injected."""
    client = DummyS3Client()
    monkeypatch.setattr(S3Service, "_create_client", lambda self: client)
    service = S3Service()
    monkeypatch.setattr(service, "normalize_image_stream_to_jpeg", lambda image: b"jpg")

    object_key = service.upload_profile_picture(
        user_id="u123",
        image=b"raw",
        bucket_name="bucket",
        source="onboarding",
    )

    assert object_key == "profiles/u123-onboarding.jpg"
    assert len(client.calls) == 1


def test_delete_profile_picture_validates_inputs():
    """delete_profile_picture validates bucket and key inputs."""
    service = S3Service(s3_client=DummyS3Client())
    with pytest.raises(ValueError, match="bucket_name must not be empty"):
        service.delete_profile_picture(
            s3_key="profiles/u1-onboarding.jpg",
            bucket_name="   ",
        )

    with pytest.raises(ValueError, match="s3_key must not be empty"):
        service.delete_profile_picture(
            s3_key="   ",
            bucket_name="bucket",
        )


def test_delete_profile_picture_deletes_expected_object():
    """delete_profile_picture calls delete_object with cleaned values."""
    client = DummyS3Client()
    service = S3Service(s3_client=client)

    service.delete_profile_picture(
        s3_key=" profiles/u123-linkedin.jpg ",
        bucket_name=" my-bucket ",
    )

    assert client.delete_calls == [{"bucket": "my-bucket", "key": "profiles/u123-linkedin.jpg"}]


def test_delete_profile_picture_uses_default_client(monkeypatch):
    """delete_profile_picture uses default client when no client is injected."""
    client = DummyS3Client()
    monkeypatch.setattr(S3Service, "_create_client", lambda self: client)
    service = S3Service()

    service.delete_profile_picture(
        s3_key="profiles/u123-onboarding.jpg",
        bucket_name="bucket",
    )

    assert client.delete_calls == [{"bucket": "bucket", "key": "profiles/u123-onboarding.jpg"}]


def test_get_profile_picture_presigned_url_validates_inputs():
    """get_profile_picture_presigned_url validates required inputs."""
    service = S3Service(s3_client=DummyS3Client())

    with pytest.raises(ValueError, match="bucket_name must not be empty"):
        service.get_profile_picture_presigned_url(
            s3_key="profiles/u1-linkedin.jpg",
            bucket_name="   ",
        )

    with pytest.raises(ValueError, match="s3_key must not be empty"):
        service.get_profile_picture_presigned_url(s3_key="  ", bucket_name="bucket")

    with pytest.raises(ValueError, match="expires_in_seconds must be greater than 0"):
        service.get_profile_picture_presigned_url(
            s3_key="profiles/u1-linkedin.jpg",
            bucket_name="bucket",
            expires_in_seconds=0,
        )


def test_get_profile_picture_presigned_url_returns_presigned_url():
    """get_profile_picture_presigned_url returns a URL for the provided key."""
    client = DummyS3Client()
    service = S3Service(s3_client=client)

    result = service.get_profile_picture_presigned_url(
        s3_key=" profiles/u123-onboarding.jpg ",
        bucket_name=" my-bucket ",
        expires_in_seconds=600,
    )

    assert result == "https://example.com/presigned"
    assert client.presign_calls == [
        {
            "client_method": "get_object",
            "params": {"Bucket": "my-bucket", "Key": "profiles/u123-onboarding.jpg"},
            "expires_in": 600,
        }
    ]


def test_get_profile_picture_presigned_url_raises_on_presign_error():
    """get_profile_picture_presigned_url wraps presign failures with RuntimeError."""

    class FailingPresignClient(DummyS3Client):
        def generate_presigned_url(self, ClientMethod, Params, ExpiresIn):  # noqa: N803
            raise Exception("boom")

    service = S3Service(s3_client=FailingPresignClient())

    with pytest.raises(RuntimeError, match="Failed to generate pre-signed URL"):
        service.get_profile_picture_presigned_url(
            s3_key="profiles/u1-linkedin.jpg",
            bucket_name="bucket",
        )


def test_generate_upload_url_validates_inputs():
    """generate_upload_url validates required inputs."""
    service = S3Service(s3_client=DummyS3Client())

    with pytest.raises(ValueError, match="bucket_name must not be empty"):
        service.generate_upload_url(
            user_id="u1",
            bucket_name="   ",
            source="onboarding",
        )

    with pytest.raises(ValueError, match="user_id must not be empty"):
        service.generate_upload_url(
            user_id=" ",
            bucket_name="bucket",
            source="onboarding",
        )

    with pytest.raises(ValueError, match="content_type must not be empty"):
        service.generate_upload_url(
            user_id="u1",
            bucket_name="bucket",
            source="onboarding",
            content_type="   ",
        )

    with pytest.raises(ValueError, match="expires_in_seconds must be greater than 0"):
        service.generate_upload_url(
            user_id="u1",
            bucket_name="bucket",
            source="onboarding",
            expires_in_seconds=0,
        )


def test_generate_upload_url_returns_put_presigned_url_and_key():
    """generate_upload_url returns upload URL metadata for direct PUT uploads."""
    client = DummyS3Client()
    service = S3Service(s3_client=client)

    result = service.generate_upload_url(
        user_id=" u123 ",
        bucket_name=" my-bucket ",
        source="onboarding",
        expires_in_seconds=900,
        content_type=" image/png ",
    )

    assert result == {
        "upload_url": "https://example.com/presigned",
        "s3_key": "profiles/u123-onboarding",
        "content_type": "image/png",
    }
    assert client.presign_calls == [
        {
            "client_method": "put_object",
            "params": {
                "Bucket": "my-bucket",
                "Key": "profiles/u123-onboarding",
                "ContentType": "image/png",
            },
            "expires_in": 900,
        }
    ]


def test_generate_upload_url_raises_on_presign_error():
    """generate_upload_url wraps presign failures with RuntimeError."""

    class FailingPresignClient(DummyS3Client):
        def generate_presigned_url(self, ClientMethod, Params, ExpiresIn):  # noqa: N803
            raise Exception("boom")

    service = S3Service(s3_client=FailingPresignClient())

    with pytest.raises(RuntimeError, match="Failed to generate upload URL"):
        service.generate_upload_url(
            user_id="u1",
            bucket_name="bucket",
            source="linkedin",
        )


def test_profile_picture_exists_validates_inputs():
    """profile_picture_exists validates required inputs."""
    service = S3Service(s3_client=DummyS3Client())

    with pytest.raises(ValueError, match="bucket_name must not be empty"):
        service.profile_picture_exists(
            s3_key="profiles/u1-onboarding",
            bucket_name="   ",
        )

    with pytest.raises(ValueError, match="s3_key must not be empty"):
        service.profile_picture_exists(
            s3_key="  ",
            bucket_name="bucket",
        )


def test_profile_picture_exists_returns_true_when_head_object_succeeds():
    """profile_picture_exists returns True when head_object succeeds."""
    client = DummyS3Client()
    service = S3Service(s3_client=client)

    result = service.profile_picture_exists(
        s3_key=" profiles/u1-onboarding ",
        bucket_name=" my-bucket ",
    )

    assert result is True
    assert client.head_calls == [
        {"bucket": "my-bucket", "key": "profiles/u1-onboarding"},
    ]


def test_profile_picture_exists_returns_false_on_not_found():
    """profile_picture_exists returns False for NoSuchKey errors."""
    client = DummyS3Client()
    client.head_exception = Exception("NoSuchKey")
    service = S3Service(s3_client=client)

    result = service.profile_picture_exists(
        s3_key="profiles/u1-onboarding",
        bucket_name="bucket",
    )

    assert result is False


def test_profile_picture_exists_raises_on_unexpected_error():
    """profile_picture_exists wraps unexpected errors in RuntimeError."""
    client = DummyS3Client()
    client.head_exception = Exception("boom")
    service = S3Service(s3_client=client)

    with pytest.raises(RuntimeError, match="Failed to verify existence"):
        service.profile_picture_exists(
            s3_key="profiles/u1-onboarding",
            bucket_name="bucket",
        )
