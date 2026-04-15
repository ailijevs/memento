"""API endpoints for analytics with role-based views.

Organizers see aggregate event data (consent breakdown, top recognized, timelines).
Attendees see their personal networking stats (people they met, their timeline).
"""

import csv
import io
import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from app.auth import CurrentUser, get_current_user
from app.dals.analytics_dal import AnalyticsDAL
from app.db.supabase import get_admin_client
from app.schemas.analytics import (
    AttendeeEventAnalytics,
    AttendeeOverview,
    EventAnalytics,
    EventComparison,
    LiveEventStatus,
    OrganizerOverview,
    PostEventReport,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])
logger = logging.getLogger(__name__)


def get_analytics_dal() -> AnalyticsDAL:
    return AnalyticsDAL(get_admin_client())


async def _verify_membership(dal: AnalyticsDAL, event_id: UUID, user_id: UUID) -> None:
    """Raise 403 if the user is not a member of the event."""
    resp = (
        dal.client.table("event_memberships")
        .select("user_id")
        .eq("event_id", str(event_id))
        .eq("user_id", str(user_id))
        .execute()
    )
    if not resp.data:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this event.",
        )


async def _is_organizer(dal: AnalyticsDAL, event_id: UUID, user_id: UUID) -> bool:
    """Check if the user is the creator (organizer) of the event."""
    resp = dal.client.table("events").select("created_by").eq("event_id", str(event_id)).execute()
    if not resp.data:
        return False
    row = resp.data[0]
    return bool(isinstance(row, dict) and row.get("created_by") == str(user_id))


# ── Overview endpoints ────────────────────────────────────────────────────


@router.get("/overview/organizer", response_model=OrganizerOverview)
async def organizer_overview(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    dal: Annotated[AnalyticsDAL, Depends(get_analytics_dal)],
) -> OrganizerOverview:
    """Aggregate stats for all events the current user has organized."""
    return await dal.get_organizer_overview(current_user.id)


@router.get("/overview/attendee", response_model=AttendeeOverview)
async def attendee_overview(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    dal: Annotated[AnalyticsDAL, Depends(get_analytics_dal)],
) -> AttendeeOverview:
    """Aggregate networking stats across all events the user has attended."""
    return await dal.get_attendee_overview(current_user.id)


# ── Per-event analytics (role-based) ─────────────────────────────────────


@router.get("/events/{event_id}/organizer", response_model=EventAnalytics)
async def event_analytics_organizer(
    event_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    dal: Annotated[AnalyticsDAL, Depends(get_analytics_dal)],
) -> EventAnalytics:
    """Full event analytics. Only accessible to the event creator."""
    if not await _is_organizer(dal, event_id, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the event organizer can view organizer analytics.",
        )
    try:
        return await dal.get_event_analytics_organizer(event_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found.",
        )


@router.get("/events/{event_id}/attendee", response_model=AttendeeEventAnalytics)
async def event_analytics_attendee(
    event_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    dal: Annotated[AnalyticsDAL, Depends(get_analytics_dal)],
) -> AttendeeEventAnalytics:
    """Personal networking stats for this event. Accessible to any event member."""
    await _verify_membership(dal, event_id, current_user.id)
    try:
        return await dal.get_event_analytics_attendee(event_id, current_user.id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found.",
        )


# ── Event comparison (organizer) ─────────────────────────────────────────


@router.get("/compare", response_model=EventComparison)
async def compare_events(
    event_a: UUID,
    event_b: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    dal: Annotated[AnalyticsDAL, Depends(get_analytics_dal)],
) -> EventComparison:
    """Side-by-side comparison of two events. Must be organizer of both."""
    for eid in [event_a, event_b]:
        if not await _is_organizer(dal, eid, current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"You must be the organizer of event {eid} to compare.",
            )
    try:
        return await dal.get_event_comparison(event_a, event_b)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


# ── Live status (organizer) ─────────────────────────────────────────────


@router.get("/events/{event_id}/live", response_model=LiveEventStatus)
async def live_event_status(
    event_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    dal: Annotated[AnalyticsDAL, Depends(get_analytics_dal)],
) -> LiveEventStatus:
    """Real-time event metrics. Only for the event organizer."""
    if not await _is_organizer(dal, event_id, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the event organizer can view live status.",
        )
    try:
        return await dal.get_live_event_status(event_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found.",
        )


# ── CSV export (organizer) ──────────────────────────────────────────────


@router.get("/events/{event_id}/export")
async def export_attendees_csv(
    event_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    dal: Annotated[AnalyticsDAL, Depends(get_analytics_dal)],
) -> StreamingResponse:
    """Export all attendees as CSV. Only for the event organizer."""
    if not await _is_organizer(dal, event_id, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the event organizer can export attendee data.",
        )

    rows = await dal.get_attendee_export(event_id)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "user_id",
            "full_name",
            "email",
            "role",
            "allow_recognition",
            "allow_profile_display",
            "joined_at",
            "times_recognized",
        ]
    )
    for r in rows:
        writer.writerow(
            [
                str(r.user_id),
                r.full_name or "",
                r.email or "",
                r.role,
                r.allow_recognition,
                r.allow_profile_display,
                r.joined_at.isoformat() if r.joined_at else "",
                r.times_recognized,
            ]
        )

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=event_{event_id}_attendees.csv"},
    )


# ── Post-event report (attendee) ────────────────────────────────────────


@router.get("/events/{event_id}/report", response_model=PostEventReport)
async def post_event_report(
    event_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    dal: Annotated[AnalyticsDAL, Depends(get_analytics_dal)],
) -> PostEventReport:
    """Personalized post-event networking report. Accessible to any event member."""
    await _verify_membership(dal, event_id, current_user.id)
    try:
        return await dal.get_post_event_report(event_id, current_user.id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found.",
        )
