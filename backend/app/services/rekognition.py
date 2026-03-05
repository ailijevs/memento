"""Helpers for AWS Rekognition operations."""

from __future__ import annotations

from typing import Any, cast
from uuid import UUID

from botocore.exceptions import ClientError
from dotenv import load_dotenv

load_dotenv()


class RekognitionError(Exception):
    """Base exception for Rekognition operations."""

    pass


class FaceNotFoundError(RekognitionError):
    """Raised when no face is detected in an image."""

    pass


class RekognitionService:
    """Service wrapper around a Rekognition client."""

    def __init__(self, rekognition_client: Any | None = None) -> None:
        self.client = rekognition_client or self._create_client()

    def ensure_collection_exists(self, *, collection_id: str) -> None:
        """Create a Rekognition collection when it does not already exist."""
        cleaned_collection_id = collection_id.strip()
        if not cleaned_collection_id:
            raise ValueError("collection_id must not be empty.")

        try:
            self.client.create_collection(CollectionId=cleaned_collection_id)
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code")
            if error_code != "ResourceAlreadyExistsException":
                raise

    def delete_collection(self, *, collection_id: str) -> dict[str, Any]:
        """Delete a Rekognition collection by ID."""
        cleaned_collection_id = collection_id.strip()
        if not cleaned_collection_id:
            raise ValueError("collection_id must not be empty.")

        try:
            response = self.client.delete_collection(CollectionId=cleaned_collection_id)
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code")
            if error_code == "ResourceNotFoundException":
                return {"StatusCode": 404}
            raise RuntimeError(
                f"Failed to delete Rekognition collection '{cleaned_collection_id}'."
            ) from exc

        return cast(dict[str, Any], response)

    def index_face_from_s3(
        self,
        *,
        collection_id: str,
        bucket_name: str,
        object_key: str,
        image_id: str,
    ) -> dict[str, Any]:
        """Index a face into a collection using an image stored in S3."""
        cleaned_collection_id = collection_id.strip()
        cleaned_bucket_name = bucket_name.strip()
        cleaned_object_key = object_key.strip()
        cleaned_image_id = image_id.strip()
        if not cleaned_collection_id:
            raise ValueError("collection_id must not be empty.")
        if not cleaned_bucket_name:
            raise ValueError("bucket_name must not be empty.")
        if not cleaned_object_key:
            raise ValueError("object_key must not be empty.")
        if not cleaned_image_id:
            raise ValueError("image_id must not be empty.")

        response = self.client.index_faces(
            CollectionId=cleaned_collection_id,
            Image={
                "S3Object": {
                    "Bucket": cleaned_bucket_name,
                    "Name": cleaned_object_key,
                }
            },
            ExternalImageId=cleaned_image_id,
            DetectionAttributes=[],
        )
        return cast(dict[str, Any], response)

    def search_faces_by_image(
        self,
        image_bytes: bytes,
        collection_id: str,
    ) -> list[dict[str, Any]]:
        """
        Search for matching faces in a frame/image capture.

        This is the primary method for MentraOS frame-based detection.

        Args:
            image_bytes: The frame image as bytes.
            collection_id: The ID of the collection to search.

        Returns:
            List of matched faces with user_id, confidence.
        """

        try:
            response = self.client.search_faces_by_image(
                CollectionId=collection_id,
                Image={"Bytes": image_bytes},
            )

            matches: list[dict[str, Any]] = []
            for match in response.get("FaceMatches", []):
                face = match["Face"]
                matches.append(
                    {
                        "user_id": face.get("ExternalImageId"),
                        "face_id": face["FaceId"],
                        "similarity": match["Similarity"],
                        "confidence": face["Confidence"],
                    }
                )

            return matches

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "InvalidParameterException":
                return []
            raise RekognitionError(f"Failed to search faces: {e}") from e

    def delete_faces_by_user(self, *, collection_id: str, user_id: UUID) -> int:
        """
        Delete all faces associated with a user.

        Args:
            user_id: The user's UUID.
            collection_id: The ID of the collection to delete the faces from.

        Returns:
            Number of faces deleted.
        """
        try:
            response = self.client.list_faces(
                CollectionId=collection_id,
            )

            face_ids_to_delete = [
                face["FaceId"]
                for face in response.get("Faces", [])
                if face.get("ExternalImageId") == str(user_id)
            ]

            if not face_ids_to_delete:
                return 0

            delete_response = self.client.delete_faces(
                CollectionId=collection_id,
                FaceIds=face_ids_to_delete,
            )
            return len(delete_response.get("DeletedFaces", []))

        except ClientError as e:
            raise RekognitionError(f"Failed to delete user faces: {e}") from e

    def _create_client(self) -> Any:
        try:
            import boto3
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "boto3 is required for Rekognition operations. "
                "Install boto3 or inject an initialized rekognition_client."
            ) from exc
        return boto3.client("rekognition")
