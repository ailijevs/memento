"""
AWS Rekognition service for facial recognition.

This module provides face detection and recognition capabilities
for identifying users from MentraOS smart glasses frame captures.
"""

import base64
from functools import lru_cache
from typing import Any
from uuid import UUID

import boto3
from botocore.exceptions import ClientError

from app.config import get_settings


class RekognitionError(Exception):
    """Base exception for Rekognition operations."""

    pass


class FaceNotFoundError(RekognitionError):
    """Raised when no face is detected in an image."""

    pass


class CollectionNotFoundError(RekognitionError):
    """Raised when the face collection doesn't exist."""

    pass


class RekognitionService:
    """
    Service for AWS Rekognition face detection and recognition.

    Handles:
    - Face collection management
    - Indexing user faces for recognition
    - Searching/matching faces from frame captures
    - Face detection in images
    """

    def __init__(self, client: Any, settings: Any) -> None:
        self._client = client
        self._settings = settings
        self._collection_id = settings.rekognition_collection_id
        self._match_threshold = settings.rekognition_face_match_threshold
        self._max_faces = settings.rekognition_max_faces

    async def ensure_collection_exists(self) -> bool:
        """
        Ensure the face collection exists, creating it if necessary.

        Returns:
            True if collection exists or was created successfully.
        """
        try:
            self._client.describe_collection(CollectionId=self._collection_id)
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceNotFoundException":
                self._client.create_collection(CollectionId=self._collection_id)
                return True
            raise RekognitionError(f"Failed to ensure collection: {e}") from e

    async def index_face(
        self,
        user_id: UUID,
        image_bytes: bytes,
        external_image_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Index a user's face in the Rekognition collection.

        Args:
            user_id: The user's UUID to associate with the face.
            image_bytes: The image containing the face as bytes.
            external_image_id: Optional custom ID, defaults to user_id string.

        Returns:
            Dict containing face_id, bounding_box, and confidence.

        Raises:
            FaceNotFoundError: If no face is detected in the image.
            RekognitionError: For other AWS errors.
        """
        external_id = external_image_id or str(user_id)

        try:
            response = self._client.index_faces(
                CollectionId=self._collection_id,
                Image={"Bytes": image_bytes},
                ExternalImageId=external_id,
                MaxFaces=1,
                QualityFilter="AUTO",
                DetectionAttributes=["DEFAULT"],
            )

            if not response.get("FaceRecords"):
                raise FaceNotFoundError("No face detected in the provided image")

            face_record = response["FaceRecords"][0]
            face = face_record["Face"]

            return {
                "face_id": face["FaceId"],
                "user_id": str(user_id),
                "external_image_id": external_id,
                "bounding_box": face["BoundingBox"],
                "confidence": face["Confidence"],
                "image_id": face.get("ImageId"),
            }

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "InvalidParameterException":
                raise FaceNotFoundError(
                    "No face detected or image quality too low"
                ) from e
            raise RekognitionError(f"Failed to index face: {e}") from e

    async def search_faces_by_image(
        self,
        image_bytes: bytes,
        max_faces: int | None = None,
        threshold: float | None = None,
    ) -> list[dict[str, Any]]:
        """
        Search for matching faces in a frame/image capture.

        This is the primary method for MentraOS frame-based detection.

        Args:
            image_bytes: The frame image as bytes.
            max_faces: Maximum faces to return (defaults to settings value).
            threshold: Minimum confidence threshold (defaults to settings value).

        Returns:
            List of matched faces with user_id, confidence, and bounding_box.
        """
        max_faces = max_faces or self._max_faces
        threshold = threshold or self._match_threshold

        try:
            response = self._client.search_faces_by_image(
                CollectionId=self._collection_id,
                Image={"Bytes": image_bytes},
                MaxFaces=max_faces,
                FaceMatchThreshold=threshold,
            )

            matches = []
            for match in response.get("FaceMatches", []):
                face = match["Face"]
                matches.append(
                    {
                        "user_id": face.get("ExternalImageId"),
                        "face_id": face["FaceId"],
                        "similarity": match["Similarity"],
                        "confidence": face["Confidence"],
                        "bounding_box": face.get("BoundingBox"),
                    }
                )

            return matches

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "InvalidParameterException":
                return []
            raise RekognitionError(f"Failed to search faces: {e}") from e

    async def detect_faces(
        self,
        image_bytes: bytes,
        attributes: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Detect all faces in an image without matching against the collection.

        Useful for validating frames contain faces before processing.

        Args:
            image_bytes: The image as bytes.
            attributes: Face attributes to return (DEFAULT or ALL).

        Returns:
            List of detected faces with bounding boxes and attributes.
        """
        attributes = attributes or ["DEFAULT"]

        try:
            response = self._client.detect_faces(
                Image={"Bytes": image_bytes},
                Attributes=attributes,
            )

            faces = []
            for face_detail in response.get("FaceDetails", []):
                faces.append(
                    {
                        "bounding_box": face_detail["BoundingBox"],
                        "confidence": face_detail["Confidence"],
                        "landmarks": face_detail.get("Landmarks", []),
                        "pose": face_detail.get("Pose", {}),
                        "quality": face_detail.get("Quality", {}),
                        "emotions": face_detail.get("Emotions", []),
                        "age_range": face_detail.get("AgeRange"),
                        "smile": face_detail.get("Smile"),
                        "eyeglasses": face_detail.get("Eyeglasses"),
                        "sunglasses": face_detail.get("Sunglasses"),
                    }
                )

            return faces

        except ClientError as e:
            raise RekognitionError(f"Failed to detect faces: {e}") from e

    async def delete_face(self, face_id: str) -> bool:
        """
        Delete a face from the collection.

        Args:
            face_id: The Rekognition face ID to delete.

        Returns:
            True if deletion was successful.
        """
        try:
            response = self._client.delete_faces(
                CollectionId=self._collection_id,
                FaceIds=[face_id],
            )
            return len(response.get("DeletedFaces", [])) > 0
        except ClientError as e:
            raise RekognitionError(f"Failed to delete face: {e}") from e

    async def delete_faces_by_user(self, user_id: UUID) -> int:
        """
        Delete all faces associated with a user.

        Args:
            user_id: The user's UUID.

        Returns:
            Number of faces deleted.
        """
        try:
            response = self._client.list_faces(
                CollectionId=self._collection_id,
                MaxResults=100,
            )

            face_ids_to_delete = [
                face["FaceId"]
                for face in response.get("Faces", [])
                if face.get("ExternalImageId") == str(user_id)
            ]

            if not face_ids_to_delete:
                return 0

            delete_response = self._client.delete_faces(
                CollectionId=self._collection_id,
                FaceIds=face_ids_to_delete,
            )
            return len(delete_response.get("DeletedFaces", []))

        except ClientError as e:
            raise RekognitionError(f"Failed to delete user faces: {e}") from e

    async def get_collection_stats(self) -> dict[str, Any]:
        """
        Get statistics about the face collection.

        Returns:
            Dict with face_count, face_model_version, and collection_arn.
        """
        try:
            response = self._client.describe_collection(
                CollectionId=self._collection_id
            )
            return {
                "collection_id": self._collection_id,
                "face_count": response.get("FaceCount", 0),
                "face_model_version": response.get("FaceModelVersion"),
                "collection_arn": response.get("CollectionARN"),
                "creation_timestamp": response.get("CreationTimestamp"),
            }
        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceNotFoundException":
                raise CollectionNotFoundError(
                    f"Collection '{self._collection_id}' not found"
                ) from e
            raise RekognitionError(f"Failed to get collection stats: {e}") from e


@lru_cache
def get_rekognition_client() -> Any:
    """Create and cache the Rekognition boto3 client."""
    settings = get_settings()

    client_kwargs: dict[str, Any] = {"region_name": settings.aws_region}

    if settings.aws_access_key_id and settings.aws_secret_access_key:
        client_kwargs["aws_access_key_id"] = settings.aws_access_key_id
        client_kwargs["aws_secret_access_key"] = settings.aws_secret_access_key

    return boto3.client("rekognition", **client_kwargs)


def get_rekognition_service() -> RekognitionService:
    """Dependency to get a RekognitionService instance."""
    return RekognitionService(
        client=get_rekognition_client(),
        settings=get_settings(),
    )


def decode_base64_image(base64_string: str) -> bytes:
    """
    Decode a base64 encoded image string to bytes.

    Handles both raw base64 and data URL formats.
    """
    if "," in base64_string:
        base64_string = base64_string.split(",", 1)[1]

    return base64.b64decode(base64_string)
