"""Pydantic schemas for analytics responses."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TimeSeriesBucket(BaseModel):
    """A single time-series data point."""

    timestamp: datetime
    count: int = 0


class ConsentBreakdown(BaseModel):
    """Consent opt-in/opt-out counts for an event."""

    recognition_opted_in: int = 0
    recognition_opted_out: int = 0
    display_opted_in: int = 0
    display_opted_out: int = 0


class TopRecognizedUser(BaseModel):
    """A frequently recognized user."""

    user_id: UUID
    full_name: str | None = None
    photo_path: str | None = None
    times_recognized: int = 0


class EventQuickStats(BaseModel):
    """Lightweight per-event stats for overview lists."""

    event_id: UUID
    name: str
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    location: str | None = None
    is_active: bool = True
    member_count: int = 0
    recognition_count: int = 0
    consent_rate: float = 0.0


class EventAnalytics(BaseModel):
    """Full analytics for a single event (organizer view)."""

    model_config = ConfigDict(from_attributes=True)

    event_id: UUID
    name: str
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    location: str | None = None
    is_active: bool = True
    indexing_status: str = "pending"

    total_members: int = 0
    total_recognitions: int = 0
    unique_recognized: int = 0
    peak_hour: str | None = None

    consent_breakdown: ConsentBreakdown = Field(default_factory=ConsentBreakdown)
    recognition_timeline: list[TimeSeriesBucket] = Field(default_factory=list)
    join_timeline: list[TimeSeriesBucket] = Field(default_factory=list)
    top_recognized: list[TopRecognizedUser] = Field(default_factory=list)


class AttendeeEventAnalytics(BaseModel):
    """Analytics visible to an event attendee (not organizer)."""

    model_config = ConfigDict(from_attributes=True)

    event_id: UUID
    name: str
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    location: str | None = None

    total_members: int = 0
    your_recognitions: int = 0
    unique_people_you_met: int = 0
    your_recognition_timeline: list[TimeSeriesBucket] = Field(default_factory=list)
    people_you_met: list[TopRecognizedUser] = Field(default_factory=list)


class OrganizerOverview(BaseModel):
    """Aggregate stats across all events the organizer created."""

    total_events: int = 0
    total_attendees: int = 0
    total_recognitions: int = 0
    avg_consent_rate: float = 0.0
    events: list[EventQuickStats] = Field(default_factory=list)


class AttendeeOverview(BaseModel):
    """Aggregate stats across all events the attendee joined."""

    total_events: int = 0
    total_people_met: int = 0
    total_recognitions: int = 0
    events: list[EventQuickStats] = Field(default_factory=list)


class EventComparison(BaseModel):
    """Side-by-side comparison of two events."""

    event_a: EventQuickStats
    event_b: EventQuickStats


class LiveEventStatus(BaseModel):
    """Real-time status for a live event."""

    event_id: UUID
    name: str
    current_members: int = 0
    recognitions_last_5min: int = 0
    total_recognitions: int = 0
    active_observers: int = 0
    recent_matches: list[TopRecognizedUser] = Field(default_factory=list)


class AttendeeExportRow(BaseModel):
    """A single row in the attendee CSV export."""

    user_id: UUID
    full_name: str | None = None
    email: str | None = None
    role: str = "attendee"
    allow_recognition: bool = False
    allow_profile_display: bool = False
    joined_at: datetime | None = None
    times_recognized: int = 0


class PostEventReport(BaseModel):
    """Personalized post-event networking report."""

    event_id: UUID
    event_name: str
    event_date: datetime | None = None
    total_attendees: int = 0
    people_you_met: int = 0
    times_you_were_recognized: int = 0
    connections: list[TopRecognizedUser] = Field(default_factory=list)
    networking_score: int = Field(
        default=0,
        description="0-100 score based on networking activity",
    )
    networking_summary: str | None = Field(
        default=None,
        description="AI-generated summary of networking performance",
    )
