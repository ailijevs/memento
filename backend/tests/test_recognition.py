"""Tests for the facial recognition feature."""

import base64
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas import (
    BoundingBox,
    FaceMatch,
    FrameDetectionResponse,
)
from app.services.rekognition import (
    RekognitionService,
    RekognitionError,
    FaceNotFoundError,
    decode_base64_image,
)


SAMPLE_IMAGE_BASE64 = base64.b64encode(b"fake-image-bytes-for-testing" * 100).decode()


class TestDecodeBase64Image:
    """Tests for base64 image decoding utility."""

    def test_decode_raw_base64(self):
        """Test decoding raw base64 string."""
        original = b"test image data"
        encoded = base64.b64encode(original).decode()
        result = decode_base64_image(encoded)
        assert result == original

    def test_decode_data_url_format(self):
        """Test decoding data URL format (with prefix)."""
        original = b"test image data"
        encoded = base64.b64encode(original).decode()
        data_url = f"data:image/jpeg;base64,{encoded}"
        result = decode_base64_image(data_url)
        assert result == original

    def test_decode_png_data_url(self):
        """Test decoding PNG data URL format."""
        original = b"png image data"
        encoded = base64.b64encode(original).decode()
        data_url = f"data:image/png;base64,{encoded}"
        result = decode_base64_image(data_url)
        assert result == original


class TestRekognitionService:
    """Tests for RekognitionService class."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock boto3 Rekognition client."""
        return MagicMock()

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = MagicMock()
        settings.rekognition_collection_id = "test-collection"
        settings.rekognition_face_match_threshold = 80.0
        settings.rekognition_max_faces = 10
        return settings

    @pytest.fixture
    def service(self, mock_client, mock_settings):
        """Create a RekognitionService instance with mocks."""
        return RekognitionService(client=mock_client, settings=mock_settings)

    @pytest.mark.asyncio
    async def test_ensure_collection_exists_when_exists(self, service, mock_client):
        """Test ensuring collection exists when it already does."""
        mock_client.describe_collection.return_value = {"FaceCount": 10}
        result = await service.ensure_collection_exists()
        assert result is True
        mock_client.describe_collection.assert_called_once()

    @pytest.mark.asyncio
    async def test_ensure_collection_creates_when_missing(self, service, mock_client):
        """Test collection is created when it doesn't exist."""
        from botocore.exceptions import ClientError

        mock_client.describe_collection.side_effect = ClientError(
            {"Error": {"Code": "ResourceNotFoundException"}},
            "DescribeCollection",
        )
        mock_client.create_collection.return_value = {}

        result = await service.ensure_collection_exists()

        assert result is True
        mock_client.create_collection.assert_called_once()

    @pytest.mark.asyncio
    async def test_index_face_success(self, service, mock_client):
        """Test successfully indexing a face."""
        user_id = uuid4()
        mock_client.index_faces.return_value = {
            "FaceRecords": [
                {
                    "Face": {
                        "FaceId": "face-123",
                        "BoundingBox": {"Width": 0.5, "Height": 0.5, "Left": 0.25, "Top": 0.25},
                        "Confidence": 99.5,
                        "ImageId": "img-123",
                    }
                }
            ]
        }

        result = await service.index_face(user_id, b"image-bytes")

        assert result["face_id"] == "face-123"
        assert result["user_id"] == str(user_id)
        assert result["confidence"] == 99.5

    @pytest.mark.asyncio
    async def test_index_face_no_face_detected(self, service, mock_client):
        """Test indexing fails when no face is detected."""
        mock_client.index_faces.return_value = {"FaceRecords": []}

        with pytest.raises(FaceNotFoundError):
            await service.index_face(uuid4(), b"image-bytes")

    @pytest.mark.asyncio
    async def test_search_faces_by_image_success(self, service, mock_client):
        """Test searching for faces returns matches."""
        mock_client.search_faces_by_image.return_value = {
            "FaceMatches": [
                {
                    "Similarity": 95.5,
                    "Face": {
                        "FaceId": "face-123",
                        "ExternalImageId": "user-uuid-123",
                        "Confidence": 99.0,
                        "BoundingBox": {"Width": 0.5, "Height": 0.5, "Left": 0.25, "Top": 0.25},
                    },
                }
            ]
        }

        result = await service.search_faces_by_image(b"image-bytes")

        assert len(result) == 1
        assert result[0]["user_id"] == "user-uuid-123"
        assert result[0]["similarity"] == 95.5

    @pytest.mark.asyncio
    async def test_search_faces_no_matches(self, service, mock_client):
        """Test search returns empty list when no matches."""
        mock_client.search_faces_by_image.return_value = {"FaceMatches": []}

        result = await service.search_faces_by_image(b"image-bytes")

        assert result == []

    @pytest.mark.asyncio
    async def test_detect_faces_success(self, service, mock_client):
        """Test detecting faces in an image."""
        mock_client.detect_faces.return_value = {
            "FaceDetails": [
                {
                    "BoundingBox": {"Width": 0.3, "Height": 0.4, "Left": 0.1, "Top": 0.2},
                    "Confidence": 99.9,
                    "Landmarks": [],
                    "Pose": {},
                    "Quality": {},
                }
            ]
        }

        result = await service.detect_faces(b"image-bytes")

        assert len(result) == 1
        assert result[0]["confidence"] == 99.9

    @pytest.mark.asyncio
    async def test_delete_faces_by_user(self, service, mock_client):
        """Test deleting all faces for a user."""
        user_id = uuid4()
        mock_client.list_faces.return_value = {
            "Faces": [
                {"FaceId": "face-1", "ExternalImageId": str(user_id)},
                {"FaceId": "face-2", "ExternalImageId": str(user_id)},
                {"FaceId": "face-3", "ExternalImageId": "other-user"},
            ]
        }
        mock_client.delete_faces.return_value = {"DeletedFaces": ["face-1", "face-2"]}

        result = await service.delete_faces_by_user(user_id)

        assert result == 2
        mock_client.delete_faces.assert_called_once_with(
            CollectionId="test-collection",
            FaceIds=["face-1", "face-2"],
        )

    @pytest.mark.asyncio
    async def test_get_collection_stats(self, service, mock_client):
        """Test getting collection statistics."""
        mock_client.describe_collection.return_value = {
            "FaceCount": 100,
            "FaceModelVersion": "6.0",
            "CollectionARN": "arn:aws:rekognition:...",
        }

        result = await service.get_collection_stats()

        assert result["face_count"] == 100
        assert result["collection_id"] == "test-collection"


class TestBoundingBoxSchema:
    """Tests for BoundingBox schema."""

    def test_valid_bounding_box(self):
        """Test creating a valid bounding box."""
        box = BoundingBox(width=0.5, height=0.5, left=0.25, top=0.25)
        assert box.width == 0.5
        assert box.height == 0.5

    def test_bounding_box_validation(self):
        """Test bounding box validates range 0-1."""
        with pytest.raises(ValueError):
            BoundingBox(width=1.5, height=0.5, left=0.25, top=0.25)


class TestFaceMatchSchema:
    """Tests for FaceMatch schema."""

    def test_face_match_with_user(self):
        """Test creating face match with user ID."""
        match = FaceMatch(
            user_id="user-123",
            face_id="face-456",
            similarity=95.5,
            confidence=99.0,
        )
        assert match.user_id == "user-123"
        assert match.similarity == 95.5

    def test_face_match_without_user(self):
        """Test face match can have null user ID."""
        match = FaceMatch(
            user_id=None,
            face_id="face-456",
            similarity=85.0,
            confidence=98.0,
        )
        assert match.user_id is None


class TestFrameDetectionResponse:
    """Tests for FrameDetectionResponse schema."""

    def test_response_with_matches(self):
        """Test response with face matches."""
        response = FrameDetectionResponse(
            matches=[
                FaceMatch(
                    user_id="user-1",
                    face_id="face-1",
                    similarity=95.0,
                    confidence=99.0,
                )
            ],
            faces_detected=2,
            processing_time_ms=150.5,
        )
        assert len(response.matches) == 1
        assert response.faces_detected == 2

    def test_response_no_matches(self):
        """Test response with no matches."""
        response = FrameDetectionResponse(
            matches=[],
            faces_detected=1,
            processing_time_ms=100.0,
        )
        assert len(response.matches) == 0
        assert response.faces_detected == 1
