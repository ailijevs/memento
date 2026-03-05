"""Helpers for Rekognition-specific identifiers."""

from __future__ import annotations

from uuid import UUID


def build_event_collection_id(event_id: UUID | str) -> str:
    """Build the Rekognition collection ID for an event."""
    cleaned_event_id = str(event_id).strip()
    if not cleaned_event_id:
        raise ValueError("event_id must not be empty.")
    return f"memento_event_{cleaned_event_id}"
