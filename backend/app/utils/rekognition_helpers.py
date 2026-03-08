"""Helpers for Rekognition-specific identifiers."""

from __future__ import annotations

import base64
from uuid import UUID


def build_event_collection_id(event_id: UUID | str) -> str:
    """Build the Rekognition collection ID for an event."""
    cleaned_event_id = str(event_id).strip()
    if not cleaned_event_id:
        raise ValueError("event_id must not be empty.")
    return f"memento_event_{cleaned_event_id}"


def decode_base64_image(base64_string: str) -> bytes:
    """
    Decode a base64 encoded image string to bytes.

    Handles both raw base64 and data URL formats.
    """
    if "," in base64_string:
        base64_string = base64_string.split(",", 1)[1]

    return base64.b64decode(base64_string)
