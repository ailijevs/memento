"""Helpers for AWS Rekognition operations."""

from __future__ import annotations

from typing import Any, cast

from botocore.exceptions import ClientError
from dotenv import load_dotenv

load_dotenv()


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

    def _create_client(self) -> Any:
        try:
            import boto3
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "boto3 is required for Rekognition operations. "
                "Install boto3 or inject an initialized rekognition_client."
            ) from exc
        return boto3.client("rekognition")
