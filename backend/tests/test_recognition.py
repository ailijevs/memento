"""Tests for the facial recognition feature."""

import base64
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.api.recognition import (
    _attach_presigned_profile_photo_urls,
    _resolve_presigned_url_ttl_seconds,
)
from app.auth.dependencies import CurrentUser, get_current_user
from app.auth.service_auth import verify_service_token
from app.main import app
from app.schemas import (
    EventProcessingStatus,
    FaceMatch,
    FrameDetectionRequest,
    FrameDetectionResponse,
    ProfileCard,
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
                ProfileCard(
                    user_id="user-1",
                    full_name="Test User",
                    headline="Engineer",
                    face_similarity=95.0,
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


# --- verify_service_token (unit) ---------------------------------------------


FAKE_USER = CurrentUser(
    id=UUID("11111111-1111-1111-1111-111111111111"),
    email="test@example.com",
    access_token="fake-jwt",
)


class TestVerifyServiceToken:
    """Unit tests for the X-Service-Token dependency."""

    @patch("app.auth.service_auth.get_settings")
    def test_skips_check_when_not_configured(self, mock_settings):
        """When no RECOGNITION_SERVICE_TOKEN is set, all requests pass."""
        mock_settings.return_value = MagicMock(recognition_service_token=None)
        verify_service_token(x_service_token=None)

    @patch("app.auth.service_auth.get_settings")
    def test_passes_when_token_matches(self, mock_settings):
        """Correct X-Service-Token passes validation."""
        mock_settings.return_value = MagicMock(
            recognition_service_token="secret-123",
        )
        verify_service_token(x_service_token="secret-123")

    @patch("app.auth.service_auth.get_settings")
    def test_rejects_missing_header(self, mock_settings):
        """Missing header returns 401 when token is configured."""
        mock_settings.return_value = MagicMock(
            recognition_service_token="secret-123",
        )
        with pytest.raises(HTTPException) as exc_info:
            verify_service_token(x_service_token=None)
        assert exc_info.value.status_code == 401
        assert "Missing" in exc_info.value.detail

    @patch("app.auth.service_auth.get_settings")
    def test_rejects_wrong_token(self, mock_settings):
        """Incorrect X-Service-Token returns 401."""
        mock_settings.return_value = MagicMock(
            recognition_service_token="secret-123",
        )
        with pytest.raises(HTTPException) as exc_info:
            verify_service_token(x_service_token="wrong-token")
        assert exc_info.value.status_code == 401
        assert "Invalid" in exc_info.value.detail


# --- API /recognition/detect --------------------------------------------------


class TestDetectEndpoint:
    """Tests for POST /api/v1/recognition/detect.

    Functional tests use ``client`` which overrides both auth dependencies
    so they can focus on business logic.  Auth-specific tests use
    ``raw_client`` with targeted patches.
    """

    SERVICE_TOKEN = "test-service-token"

    @pytest.fixture
    def client(self):
        """TestClient with both auth dependencies bypassed."""
        app.dependency_overrides[get_current_user] = lambda: FAKE_USER
        app.dependency_overrides[verify_service_token] = lambda: None
        yield TestClient(app)
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(verify_service_token, None)

    @pytest.fixture
    def raw_client(self):
        """TestClient without auth overrides."""
        return TestClient(app)

    # -- functional tests (auth bypassed) --

    @patch("app.api.recognition.ProfileCardBuilder")
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
        mock_card_builder_cls,
        client,
    ):
        """Detect returns 200 and FrameDetectionResponse with profile cards."""
        mock_get_admin.return_value = MagicMock()
        mock_decode.return_value = b"decoded-image-bytes"
        mock_build_collection.return_value = "memento_faces"
        svc = MagicMock()
        svc.search_all_faces_in_frame.return_value = [
            {
                "user_id": "user-1",
                "face_id": "f1",
                "similarity": 90.0,
                "confidence": 98.0,
            }
        ]
        mock_service_cls.return_value = svc

        card_builder = MagicMock()
        card_builder.build_cards = AsyncMock(
            return_value=[
                ProfileCard(
                    user_id="user-1",
                    full_name="Test User",
                    headline="Engineer",
                    face_similarity=90.0,
                )
            ]
        )
        mock_card_builder_cls.return_value = card_builder

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
        assert data["matches"][0]["full_name"] == "Test User"
        assert "processing_time_ms" in data
        mock_decode.assert_called_once()
        svc.search_all_faces_in_frame.assert_called_once_with(
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
        svc.search_all_faces_in_frame.side_effect = RekognitionError("service down")
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
            ends_at=None,
        )
        mock_dal_cls.return_value = dal
        svc = MagicMock()
        svc.search_all_faces_in_frame.return_value = []
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
        svc.search_all_faces_in_frame.assert_called_once_with(
            image_bytes=b"bytes",
            collection_id="memento_event_abc",
        )

    # -- auth tests (no overrides) --

    def test_detect_missing_jwt_returns_401(self, raw_client):
        """Missing Authorization header (no JWT) returns 401."""
        response = raw_client.post(
            "/api/v1/recognition/detect",
            json={
                "image_base64": SAMPLE_IMAGE_BASE64,
                "event_id": None,
            },
        )
        assert response.status_code == 401

    @patch("app.auth.service_auth.get_settings")
    def test_detect_missing_service_token_returns_401(
        self,
        mock_settings,
        raw_client,
    ):
        """Missing X-Service-Token returns 401 when token is configured."""
        mock_settings.return_value = MagicMock(
            recognition_service_token=self.SERVICE_TOKEN,
        )
        app.dependency_overrides[get_current_user] = lambda: FAKE_USER
        try:
            response = raw_client.post(
                "/api/v1/recognition/detect",
                json={
                    "image_base64": SAMPLE_IMAGE_BASE64,
                    "event_id": None,
                },
            )
            assert response.status_code == 401
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    @patch("app.auth.service_auth.get_settings")
    def test_detect_invalid_service_token_returns_401(
        self,
        mock_settings,
        raw_client,
    ):
        """Wrong X-Service-Token returns 401."""
        mock_settings.return_value = MagicMock(
            recognition_service_token=self.SERVICE_TOKEN,
        )
        app.dependency_overrides[get_current_user] = lambda: FAKE_USER
        try:
            response = raw_client.post(
                "/api/v1/recognition/detect",
                json={
                    "image_base64": SAMPLE_IMAGE_BASE64,
                    "event_id": None,
                },
                headers={"X-Service-Token": "wrong-token"},
            )
            assert response.status_code == 401
        finally:
            app.dependency_overrides.pop(get_current_user, None)


class TestPresignedProfilePhotoUrls:
    """Tests for pre-signed profile photo URL attachment."""

    @patch("app.api.recognition.S3Service")
    @patch("app.api.recognition.get_settings")
    @patch("app.api.recognition._resolve_presigned_url_ttl_seconds")
    def test_attach_passes_computed_ttl_to_s3_service(
        self,
        mock_resolve_ttl,
        mock_get_settings,
        mock_s3_service_cls,
    ):
        """Attach helper passes resolved TTL to S3 pre-sign call."""
        mock_get_settings.return_value = MagicMock(s3_bucket_name="bucket")
        mock_resolve_ttl.return_value = 321
        mock_s3_service = MagicMock()
        mock_s3_service.get_profile_picture_presigned_url.return_value = "https://example.com/url"
        mock_s3_service_cls.return_value = mock_s3_service

        cards = [
            ProfileCard(
                user_id="user-1",
                full_name="Test User",
                headline="Engineer",
                face_similarity=90.0,
                photo_path="profiles/user-1-onboarding.jpg",
            )
        ]
        event_end_time = datetime.now(timezone.utc) + timedelta(hours=1)

        result = _attach_presigned_profile_photo_urls(
            profile_cards=cards,
            event_end_time=event_end_time,
        )

        assert result[0].photo_path == "https://example.com/url"
        mock_resolve_ttl.assert_called_once_with(event_end_time)
        mock_s3_service.get_profile_picture_presigned_url.assert_called_once_with(
            s3_key="profiles/user-1-onboarding.jpg",
            bucket_name="bucket",
            expires_in_seconds=321,
        )

    def test_resolve_ttl_defaults_to_ten_minutes_when_event_ended(self):
        """Expired events use 10-minute fallback TTL."""
        expired_end_time = datetime.now(timezone.utc) - timedelta(seconds=5)
        assert _resolve_presigned_url_ttl_seconds(expired_end_time) == 600

    def test_resolve_ttl_defaults_to_ten_minutes_when_event_end_missing(self):
        """Missing event end time uses 10-minute fallback TTL."""
        assert _resolve_presigned_url_ttl_seconds(None) == 600
