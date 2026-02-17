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


class DummyS3Client:
    """Capture upload inputs for assertions."""

    def __init__(self) -> None:
        self.calls: list[dict] = []

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


def _png_bytes(mode: str = "RGB") -> bytes:
    pillow = pytest.importorskip("PIL")
    image = pillow.Image.new(mode, (3, 3), (10, 20, 30, 255) if "A" in mode else (10, 20, 30))
    out = BytesIO()
    image.save(out, format="PNG")
    return out.getvalue()


def test_read_image_bytes_supports_raw_bytes_and_streams():
    """_read_image_bytes returns bytes for both bytes and stream inputs."""
    assert s3._read_image_bytes(b"abc") == b"abc"
    assert s3._read_image_bytes(BytesIO(b"def")) == b"def"


def test_normalize_image_stream_to_jpeg_returns_jpeg_bytes():
    """normalize_image_stream_to_jpeg returns JPEG-encoded bytes."""
    result = s3.normalize_image_stream_to_jpeg(_png_bytes())
    assert result[:2] == b"\xff\xd8"
    assert len(result) > 10


def test_normalize_image_stream_to_jpeg_accepts_stream_input():
    """normalize_image_stream_to_jpeg accepts binary stream input."""
    result = s3.normalize_image_stream_to_jpeg(BytesIO(_png_bytes()))
    assert result[:2] == b"\xff\xd8"


@pytest.mark.parametrize("quality", [0, 96])
def test_normalize_image_stream_to_jpeg_rejects_invalid_quality(quality):
    """normalize_image_stream_to_jpeg rejects out-of-range quality."""
    with pytest.raises(ValueError, match="quality must be between 1 and 95"):
        s3.normalize_image_stream_to_jpeg(_png_bytes(), quality=quality)


@pytest.mark.parametrize("payload", [b"", BytesIO(b"")])
def test_normalize_image_stream_to_jpeg_rejects_empty_images(payload):
    """normalize_image_stream_to_jpeg rejects empty payloads."""
    with pytest.raises(ValueError, match="image must not be empty"):
        s3.normalize_image_stream_to_jpeg(payload)


def test_normalize_image_stream_to_jpeg_raises_when_pillow_missing(monkeypatch):
    """normalize_image_stream_to_jpeg raises runtime error when PIL is unavailable."""
    real_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "PIL":
            raise ImportError("No module named PIL")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    with pytest.raises(RuntimeError, match="Pillow is required to normalize images"):
        s3.normalize_image_stream_to_jpeg(b"not-empty")


def test_to_rgb_returns_rgb_for_rgba():
    """_to_rgb flattens RGBA input into RGB."""
    pillow = pytest.importorskip("PIL")
    rgba = pillow.Image.new("RGBA", (2, 2), (40, 50, 60, 120))
    converted = s3._to_rgb(rgba)
    assert converted.mode == "RGB"


def test_to_rgb_converts_non_rgb_modes():
    """_to_rgb converts non-RGB modes to RGB."""
    pillow = pytest.importorskip("PIL")
    grayscale = pillow.Image.new("L", (2, 2), 200)
    converted = s3._to_rgb(grayscale)
    assert converted.mode == "RGB"


def test_to_rgb_returns_original_rgb_image():
    """_to_rgb returns original object when already RGB."""
    pillow = pytest.importorskip("PIL")
    rgb = pillow.Image.new("RGB", (2, 2), (1, 2, 3))
    converted = s3._to_rgb(rgb)
    assert converted is rgb


def test_create_s3_client_constructs_boto3_client(monkeypatch):
    """_create_s3_client delegates to boto3.client('s3')."""
    calls = []
    fake_client = object()
    fake_boto3 = SimpleNamespace(
        client=lambda service_name: calls.append(service_name) or fake_client
    )
    monkeypatch.setitem(sys.modules, "boto3", fake_boto3)

    created = s3._create_s3_client()
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
    with pytest.raises(RuntimeError, match="boto3 is required to upload profile pictures"):
        s3._create_s3_client()


def test_upload_profile_picture_validates_inputs(monkeypatch):
    """upload_profile_picture validates bucket and image payload."""
    monkeypatch.setattr(s3, "normalize_image_stream_to_jpeg", lambda image: image)
    with pytest.raises(ValueError, match="bucket_name must not be empty"):
        s3.upload_profile_picture(
            user_id="u1",
            image=b"payload",
            bucket_name="   ",
            source="onboarding",
            s3_client=DummyS3Client(),
        )
    with pytest.raises(ValueError, match="image must not be empty"):
        s3.upload_profile_picture(
            user_id="u1",
            image=b"",
            bucket_name="bucket",
            source="onboarding",
            s3_client=DummyS3Client(),
        )


def test_upload_profile_picture_normalizes_and_uploads_with_expected_metadata(monkeypatch):
    """upload_profile_picture uploads normalized JPEG with expected metadata."""
    client = DummyS3Client()
    observed = {}

    def fake_normalize(image: bytes) -> bytes:
        observed["input"] = image
        return b"jpeg-bytes"

    monkeypatch.setattr(s3, "normalize_image_stream_to_jpeg", fake_normalize)

    user_id = str(uuid4())
    object_key = s3.upload_profile_picture(
        user_id=user_id,
        image=BytesIO(b"original-image"),
        bucket_name=" my-bucket ",
        source="linkedin",
        s3_client=client,
    )

    assert observed["input"] == b"original-image"
    assert object_key == f"profiles/{user_id}-linkedin.jpg"
    assert len(client.calls) == 1
    assert client.calls[0]["bytes"] == b"jpeg-bytes"
    assert client.calls[0]["bucket"] == "my-bucket"
    assert client.calls[0]["key"] == f"profiles/{user_id}-linkedin.jpg"
    assert client.calls[0]["extra_args"] == {"ContentType": "image/jpeg"}


def test_upload_profile_picture_uses_default_s3_client(monkeypatch):
    """upload_profile_picture uses _create_s3_client when no client is injected."""
    client = DummyS3Client()
    monkeypatch.setattr(s3, "_create_s3_client", lambda: client)
    monkeypatch.setattr(s3, "normalize_image_stream_to_jpeg", lambda image: b"jpg")

    object_key = s3.upload_profile_picture(
        user_id="u123",
        image=b"raw",
        bucket_name="bucket",
        source="onboarding",
    )

    assert object_key == "profiles/u123-onboarding.jpg"
    assert len(client.calls) == 1
