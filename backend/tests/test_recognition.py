"""Tests for the facial recognition feature."""

import base64
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas import (
    EventProcessingStatus,
    FaceMatch,
    FrameDetectionRequest,
    FrameDetectionResponse,
)
from app.services.rekognition import (
    RekognitionError,
    RekognitionService,
)
from app.utils.rekognition_helpers import (
    build_event_collection_id,
    decode_base64_image,
)

# Minimum length for FrameDetectionRequest.image_base64
SAMPLE_IMAGE_BASE64 = base64.b64encode(b"fake-image-bytes-for-testing" * 100).decode()


# --- rekognition_helpers -----------------------------------------------------


class TestDecodeBase64Image:
    """Tests for decode_base64_image."""

    def test_decode_raw_base64(self):
        """Decode raw base64 string to bytes."""
        original = b"test image data"
        encoded = base64.b64encode(original).decode()
        assert decode_base64_image(encoded) == original

    def test_decode_data_url_format(self):
        """Decode data URL format (data:image/jpeg;base64,...)."""
        original = b"test image data"
        encoded = base64.b64encode(original).decode()
        data_url = f"data:image/jpeg;base64,{encoded}"
        assert decode_base64_image(data_url) == original

    def test_decode_png_data_url(self):
        """Decode PNG data URL format."""
        original = b"png image data"
        encoded = base64.b64encode(original).decode()
        data_url = f"data:image/png;base64,{encoded}"
        assert decode_base64_image(data_url) == original


class TestBuildEventCollectionId:
    """Tests for build_event_collection_id."""

    def test_with_uuid(self):
        """Build collection ID from UUID."""
        event_id = uuid4()
        got = build_event_collection_id(event_id)
        assert got == f"memento_event_{event_id}"

    def test_with_string(self):
        """Build collection ID from string."""
        got = build_event_collection_id("abc-123")
        assert got == "memento_event_abc-123"

    def test_empty_string_raises(self):
        """Empty event_id raises ValueError."""
        with pytest.raises(ValueError, match="must not be empty"):
            build_event_collection_id("")


# --- RekognitionService ------------------------------------------------------


class TestRekognitionService:
    """Tests for RekognitionService (sync API)."""

    @pytest.fixture
    def mock_client(self):
        return MagicMock()

    @pytest.fixture
    def service(self, mock_client):
        return RekognitionService(rekognition_client=mock_client)

    def test_ensure_collection_exists_creates(self, service, mock_client):
        """Creates collection when it does not exist."""
        service.ensure_collection_exists(collection_id="test-collection")
        mock_client.create_collection.assert_called_once_with(CollectionId="test-collection")

    def test_ensure_collection_exists_ignores_already_exists(self, service, mock_client):
        """Does not raise when collection already exists."""
        from botocore.exceptions import ClientError

        mock_client.create_collection.side_effect = ClientError(
            {"Error": {"Code": "ResourceAlreadyExistsException"}},
            "CreateCollection",
        )
        service.ensure_collection_exists(collection_id="existing")
        mock_client.create_collection.assert_called_once()

    def test_ensure_collection_exists_empty_id_raises(self, service):
        """Empty collection_id raises ValueError."""
        with pytest.raises(ValueError, match="must not be empty"):
            service.ensure_collection_exists(collection_id="   ")

    def test_delete_collection_success(self, service, mock_client):
        """delete_collection returns response."""
        mock_client.delete_collection.return_value = {"StatusCode": 200}
        got = service.delete_collection(collection_id="coll-1")
        assert got["StatusCode"] == 200
        mock_client.delete_collection.assert_called_once_with(CollectionId="coll-1")

    def test_delete_collection_not_found_returns_404(self, service, mock_client):
        """ResourceNotFoundException returns dict with StatusCode 404."""
        from botocore.exceptions import ClientError

        mock_client.delete_collection.side_effect = ClientError(
            {"Error": {"Code": "ResourceNotFoundException"}},
            "DeleteCollection",
        )
        got = service.delete_collection(collection_id="missing")
        assert got["StatusCode"] == 404

    def test_search_faces_by_image_returns_matches(self, service, mock_client):
        """search_faces_by_image returns normalized list of matches."""
        mock_client.search_faces_by_image.return_value = {
            "FaceMatches": [
                {
                    "Similarity": 95.5,
                    "Face": {
                        "FaceId": "face-123",
                        "ExternalImageId": "user-uuid-123",
                        "Confidence": 99.0,
                    },
                }
            ]
        }
        result = service.search_faces_by_image(
            image_bytes=b"image-bytes",
            collection_id="memento_event_xyz",
        )
        assert len(result) == 1
        assert result[0]["user_id"] == "user-uuid-123"
        assert result[0]["face_id"] == "face-123"
        assert result[0]["similarity"] == 95.5
        assert result[0]["confidence"] == 99.0
        mock_client.search_faces_by_image.assert_called_once_with(
            CollectionId="memento_event_xyz",
            Image={"Bytes": b"image-bytes"},
        )

    def test_search_faces_by_image_no_matches(self, service, mock_client):
        """Empty FaceMatches returns empty list."""
        mock_client.search_faces_by_image.return_value = {"FaceMatches": []}
        result = service.search_faces_by_image(
            image_bytes=b"bytes",
            collection_id="coll",
        )
        assert result == []

    def test_search_faces_by_image_invalid_parameter_returns_empty(self, service, mock_client):
        """InvalidParameterException (e.g. no face) returns empty list."""
        from botocore.exceptions import ClientError

        mock_client.search_faces_by_image.side_effect = ClientError(
            {"Error": {"Code": "InvalidParameterException"}},
            "SearchFacesByImage",
        )
        result = service.search_faces_by_image(
            image_bytes=b"bytes",
            collection_id="coll",
        )
        assert result == []

    def test_search_faces_by_image_other_client_error_raises(self, service, mock_client):
        """Other ClientError is wrapped in RekognitionError."""
        from botocore.exceptions import ClientError

        mock_client.search_faces_by_image.side_effect = ClientError(
            {"Error": {"Code": "ThrottlingException"}},
            "SearchFacesByImage",
        )
        with pytest.raises(RekognitionError):
            service.search_faces_by_image(
                image_bytes=b"bytes",
                collection_id="coll",
            )

    def test_index_face_from_s3_calls_client(self, service, mock_client):
        """index_face_from_s3 calls index_faces with S3 object."""
        mock_client.index_faces.return_value = {
            "FaceRecords": [
                {
                    "Face": {
                        "FaceId": "f1",
                        "Confidence": 99.0,
                    }
                }
            ]
        }
        service.index_face_from_s3(
            collection_id="coll",
            bucket_name="bucket",
            object_key="key.jpg",
            image_id="user-uuid",
        )
        mock_client.index_faces.assert_called_once()
        call_kw = mock_client.index_faces.call_args[1]
        assert call_kw["CollectionId"] == "coll"
        assert call_kw["Image"]["S3Object"]["Bucket"] == "bucket"
        assert call_kw["Image"]["S3Object"]["Name"] == "key.jpg"
        assert call_kw["ExternalImageId"] == "user-uuid"

    def test_delete_faces_by_user(self, service, mock_client):
        """delete_faces_by_user deletes only faces for that user."""
        user_id = uuid4()
        mock_client.list_faces.return_value = {
            "Faces": [
                {"FaceId": "face-1", "ExternalImageId": str(user_id)},
                {"FaceId": "face-2", "ExternalImageId": str(user_id)},
                {"FaceId": "face-3", "ExternalImageId": "other-user"},
            ]
        }
        mock_client.delete_faces.return_value = {"DeletedFaces": ["face-1", "face-2"]}
        count = service.delete_faces_by_user(
            collection_id="coll",
            user_id=user_id,
        )
        assert count == 2
        mock_client.delete_faces.assert_called_once_with(
            CollectionId="coll",
            FaceIds=["face-1", "face-2"],
        )

    def test_delete_faces_by_user_none_to_delete(self, service, mock_client):
        """Returns 0 when no faces for user."""
        user_id = uuid4()
        mock_client.list_faces.return_value = {"Faces": []}
        count = service.delete_faces_by_user(
            collection_id="coll",
            user_id=user_id,
        )
        assert count == 0
        mock_client.delete_faces.assert_not_called()


# --- Schemas ------------------------------------------------------------------


class TestFaceMatchSchema:
    """Tests for FaceMatch schema."""

    def test_face_match_with_user(self):
        match = FaceMatch(
            user_id="user-123",
            face_id="face-456",
            similarity=95.5,
            confidence=99.0,
        )
        assert match.user_id == "user-123"
        assert match.similarity == 95.5

    def test_face_match_user_id_optional(self):
        match = FaceMatch(
            user_id=None,
            face_id="face-456",
            similarity=85.0,
            confidence=98.0,
        )
        assert match.user_id is None


class TestFrameDetectionRequestSchema:
    """Tests for FrameDetectionRequest schema."""

    def test_min_length_image_base64(self):
        """image_base64 has min_length=100."""
        with pytest.raises(ValueError):
            FrameDetectionRequest(image_base64="short")

    def test_event_id_optional(self):
        req = FrameDetectionRequest(
            image_base64=SAMPLE_IMAGE_BASE64,
            event_id=None,
        )
        assert req.event_id is None

    def test_event_id_provided(self):
        eid = uuid4()
        req = FrameDetectionRequest(
            image_base64=SAMPLE_IMAGE_BASE64,
            event_id=eid,
        )
        assert req.event_id == eid


class TestFrameDetectionResponseSchema:
    """Tests for FrameDetectionResponse schema."""

    def test_response_with_matches(self):
        response = FrameDetectionResponse(
            matches=[
                FaceMatch(
                    user_id="user-1",
                    face_id="face-1",
                    similarity=95.0,
                    confidence=99.0,
                )
            ],
            processing_time_ms=150.5,
            event_id=None,
        )
        assert len(response.matches) == 1
        assert response.processing_time_ms == 150.5
        assert response.event_id is None

    def test_response_no_matches(self):
        response = FrameDetectionResponse(
            matches=[],
            processing_time_ms=100.0,
        )
        assert len(response.matches) == 0
        assert response.processing_time_ms == 100.0


# --- API /recognition/detect --------------------------------------------------


class TestDetectEndpoint:
    """Tests for POST /api/v1/recognition/detect."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    @patch("app.api.recognition.decode_base64_image")
    @patch("app.api.recognition.build_event_collection_id")
    @patch("app.api.recognition.RekognitionService")
    @patch("app.api.recognition.get_admin_client")
    def test_detect_returns_200_with_matches(
        self,
        mock_get_admin,
        mock_service_cls,
        mock_build_collection,
        mock_decode,
        client,
    ):
        """Detect returns 200 and FrameDetectionResponse with matches."""
        mock_get_admin.return_value = MagicMock()
        mock_decode.return_value = b"decoded-image-bytes"
        mock_build_collection.return_value = "memento_faces"
        svc = MagicMock()
        svc.search_faces_by_image.return_value = [
            {
                "user_id": "user-1",
                "face_id": "f1",
                "similarity": 90.0,
                "confidence": 98.0,
            }
        ]
        mock_service_cls.return_value = svc

        response = client.post(
            "/api/v1/recognition/detect",
            json={
                "image_base64": SAMPLE_IMAGE_BASE64,
                "event_id": None,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "matches" in data
        assert len(data["matches"]) == 1
        assert data["matches"][0]["user_id"] == "user-1"
        assert "processing_time_ms" in data
        mock_decode.assert_called_once()
        svc.search_faces_by_image.assert_called_once_with(
            image_bytes=b"decoded-image-bytes",
            collection_id="memento_faces",
        )

    @patch("app.api.recognition.decode_base64_image")
    @patch("app.api.recognition.RekognitionService")
    @patch("app.api.recognition.get_admin_client")
    def test_detect_invalid_base64_returns_400(
        self,
        mock_get_admin,
        mock_service_cls,
        mock_decode,
        client,
    ):
        """Invalid base64 image returns 400."""
        mock_get_admin.return_value = MagicMock()
        mock_decode.side_effect = ValueError("bad base64")

        response = client.post(
            "/api/v1/recognition/detect",
            json={
                "image_base64": SAMPLE_IMAGE_BASE64,
                "event_id": None,
            },
        )

        assert response.status_code == 400
        assert "Invalid base64" in response.json()["detail"]

    @patch("app.api.recognition.decode_base64_image")
    @patch("app.api.recognition.RekognitionService")
    @patch("app.api.recognition.get_admin_client")
    def test_detect_rekognition_error_returns_502(
        self,
        mock_get_admin,
        mock_service_cls,
        mock_decode,
        client,
    ):
        """RekognitionError from service returns 502."""
        mock_get_admin.return_value = MagicMock()
        mock_decode.return_value = b"bytes"
        svc = MagicMock()
        svc.search_faces_by_image.side_effect = RekognitionError("service down")
        mock_service_cls.return_value = svc

        response = client.post(
            "/api/v1/recognition/detect",
            json={
                "image_base64": SAMPLE_IMAGE_BASE64,
                "event_id": None,
            },
        )

        assert response.status_code == 502
        assert "Recognition service error" in response.json()["detail"]

    @patch("app.api.recognition.EventDAL")
    @patch("app.api.recognition.decode_base64_image")
    @patch("app.api.recognition.build_event_collection_id")
    @patch("app.api.recognition.RekognitionService")
    @patch("app.api.recognition.get_admin_client")
    def test_detect_with_event_id_uses_event_collection(
        self,
        mock_get_admin,
        mock_service_cls,
        mock_build_collection,
        mock_decode,
        mock_dal_cls,
        client,
    ):
        """When event_id is provided, collection_id is built from event."""
        mock_get_admin.return_value = MagicMock()
        mock_decode.return_value = b"bytes"
        mock_build_collection.return_value = "memento_event_abc"
        dal = AsyncMock()
        dal.get_by_id.return_value = MagicMock(
            event_id=uuid4(),
            indexing_status=EventProcessingStatus.COMPLETED,
        )
        mock_dal_cls.return_value = dal
        svc = MagicMock()
        svc.search_faces_by_image.return_value = []
        mock_service_cls.return_value = svc

        event_id = uuid4()
        response = client.post(
            "/api/v1/recognition/detect",
            json={
                "image_base64": SAMPLE_IMAGE_BASE64,
                "event_id": str(event_id),
            },
        )

        assert response.status_code == 200
        mock_build_collection.assert_called_once_with(event_id)
        svc.search_faces_by_image.assert_called_once_with(
            image_bytes=b"bytes",
            collection_id="memento_event_abc",
        )
