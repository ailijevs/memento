"""Service modules for external integrations."""

from .rekognition import RekognitionService, get_rekognition_service

__all__ = [
    "RekognitionService",
    "get_rekognition_service",
]
