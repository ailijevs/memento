"""Tests for app.services.rekognition."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from botocore.exceptions import ClientError

_ROOT = str(Path(__file__).resolve().parents[3])
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
rekognition_module = importlib.import_module("app.services.rekognition")
RekognitionService = rekognition_module.RekognitionService


class DummyRekognitionClient:
    """Capture Rekognition calls for assertions."""

    def __init__(self) -> None:
        self.create_calls: list[dict[str, str]] = []
        self.index_calls: list[dict[str, object]] = []
        self.raise_already_exists = False

    def create_collection(self, CollectionId):  # noqa: N803
        self.create_calls.append({"CollectionId": CollectionId})
        if self.raise_already_exists:
            raise ClientError(
                {
                    "Error": {
                        "Code": "ResourceAlreadyExistsException",
                        "Message": "exists",
                    }
                },
                "CreateCollection",
            )
        return {"StatusCode": 200}

    def index_faces(self, **kwargs):
        self.index_calls.append(kwargs)
        return {"FaceRecords": []}


def test_ensure_collection_exists_creates_collection():
    """ensure_collection_exists creates collection for new ID."""
    client = DummyRekognitionClient()
    service = RekognitionService(rekognition_client=client)
    service.ensure_collection_exists(collection_id="collection-1")
    assert client.create_calls == [{"CollectionId": "collection-1"}]


def test_ensure_collection_exists_ignores_existing_collection_error():
    """ensure_collection_exists ignores already-exists response from AWS."""
    client = DummyRekognitionClient()
    client.raise_already_exists = True
    service = RekognitionService(rekognition_client=client)
    service.ensure_collection_exists(collection_id="collection-1")
    assert client.create_calls == [{"CollectionId": "collection-1"}]


def test_ensure_collection_exists_validates_collection_id():
    """ensure_collection_exists validates non-empty collection ID."""
    service = RekognitionService(rekognition_client=DummyRekognitionClient())
    with pytest.raises(ValueError, match="collection_id must not be empty"):
        service.ensure_collection_exists(collection_id="   ")


def test_index_face_from_s3_sends_expected_payload():
    """index_face_from_s3 forwards S3 object fields and image ID."""
    client = DummyRekognitionClient()
    service = RekognitionService(rekognition_client=client)
    response = service.index_face_from_s3(
        collection_id="collection-1",
        bucket_name="bucket-a",
        object_key="profiles/u1.jpg",
        image_id="user-1",
    )

    assert response == {"FaceRecords": []}
    assert client.index_calls == [
        {
            "CollectionId": "collection-1",
            "Image": {"S3Object": {"Bucket": "bucket-a", "Name": "profiles/u1.jpg"}},
            "ExternalImageId": "user-1",
            "DetectionAttributes": [],
        }
    ]


def test_index_face_from_s3_validates_inputs():
    """index_face_from_s3 validates required fields."""
    service = RekognitionService(rekognition_client=DummyRekognitionClient())

    with pytest.raises(ValueError, match="collection_id must not be empty"):
        service.index_face_from_s3(
            collection_id=" ",
            bucket_name="bucket",
            object_key="obj",
            image_id="id",
        )
    with pytest.raises(ValueError, match="bucket_name must not be empty"):
        service.index_face_from_s3(
            collection_id="collection",
            bucket_name=" ",
            object_key="obj",
            image_id="id",
        )
    with pytest.raises(ValueError, match="object_key must not be empty"):
        service.index_face_from_s3(
            collection_id="collection",
            bucket_name="bucket",
            object_key=" ",
            image_id="id",
        )
    with pytest.raises(ValueError, match="image_id must not be empty"):
        service.index_face_from_s3(
            collection_id="collection",
            bucket_name="bucket",
            object_key="obj",
            image_id=" ",
        )


def test_rekognition_service_uses_default_client_factory(monkeypatch):
    """Service uses boto3 client when no client is injected."""
    client = DummyRekognitionClient()
    fake_boto3 = SimpleNamespace(
        client=lambda service_name, **kwargs: client if service_name == "rekognition" else None
    )
    monkeypatch.setitem(sys.modules, "boto3", fake_boto3)

    service = RekognitionService()
    assert service.client is client
