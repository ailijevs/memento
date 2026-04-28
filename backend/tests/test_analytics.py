"""Tests for analytics endpoints with role-based access control."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.auth.dependencies import CurrentUser, get_current_user
from app.main import app

ORGANIZER_ID = "00000000-0000-0000-0000-000000000001"
ATTENDEE_ID = "00000000-0000-0000-0000-000000000002"
EVENT_ID = "00000000-0000-0000-0000-eeeeeeeeee01"
EVENT_ID_B = "00000000-0000-0000-0000-eeeeeeeeee02"

ORGANIZER = CurrentUser(
    id=UUID(ORGANIZER_ID),
    email="organizer@example.com",
    access_token="fake-organizer-token",
)

ATTENDEE = CurrentUser(
    id=UUID(ATTENDEE_ID),
    email="attendee@example.com",
    access_token="fake-attendee-token",
)


def _make_chainable(mock_q, resp):
    """Wire up a chainable mock so both list and maybe_single paths work."""
    mock_q.select.return_value = mock_q
    mock_q.insert.return_value = mock_q
    mock_q.eq.return_value = mock_q
    mock_q.neq.return_value = mock_q
    mock_q.in_.return_value = mock_q
    mock_q.gte.return_value = mock_q
    mock_q.lte.return_value = mock_q
    mock_q.order.return_value = mock_q
    mock_q.limit.return_value = mock_q
    mock_q.execute.return_value = resp

    single_resp = MagicMock()
    if isinstance(resp.data, list) and resp.data:
        single_resp.data = resp.data[0]
    elif isinstance(resp.data, list):
        single_resp.data = None
    else:
        single_resp.data = resp.data
    single_resp.count = resp.count

    single_q = MagicMock()
    single_q.execute.return_value = single_resp
    mock_q.maybe_single.return_value = single_q

    return mock_q


def _build_admin_client(
    events=None,
    memberships=None,
    consents=None,
    recog_logs=None,
    recog_attempts=None,
    profiles=None,
):
    """Build a mock admin client with configurable table responses."""
    events = events or []
    memberships = memberships or []
    consents = consents or []
    recog_logs = recog_logs or []
    recog_attempts = recog_attempts or []
    profiles = profiles or []

    client = MagicMock()

    def table_router(name):
        mock_q = MagicMock()
        resp = MagicMock()

        if name == "events":
            resp.data = events
            resp.count = len(events)
        elif name == "event_memberships":
            resp.data = memberships
            resp.count = len(memberships)
        elif name == "event_consents":
            resp.data = consents
            resp.count = len(consents)
        elif name == "recognition_logs":
            resp.data = recog_logs
            resp.count = len(recog_logs)
        elif name == "recognition_attempts":
            resp.data = recog_attempts
            resp.count = len(recog_attempts)
        elif name == "profiles":
            resp.data = profiles
            resp.count = len(profiles)
        else:
            resp.data = []
            resp.count = 0

        return _make_chainable(mock_q, resp)

    client.table = table_router
    return client


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def organizer_client():
    app.dependency_overrides[get_current_user] = lambda: ORGANIZER
    c = TestClient(app)
    yield c
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def attendee_client():
    app.dependency_overrides[get_current_user] = lambda: ATTENDEE
    c = TestClient(app)
    yield c
    app.dependency_overrides.pop(get_current_user, None)


# ── Auth required ────────────────────────────────────────────────────────


class TestAnalyticsAuthRequired:
    """All analytics endpoints require authentication."""

    endpoints = [
        ("/api/v1/analytics/overview/organizer", "GET"),
        ("/api/v1/analytics/overview/attendee", "GET"),
        (f"/api/v1/analytics/events/{EVENT_ID}/organizer", "GET"),
        (f"/api/v1/analytics/events/{EVENT_ID}/attendee", "GET"),
        (f"/api/v1/analytics/events/{EVENT_ID}/live", "GET"),
        (f"/api/v1/analytics/events/{EVENT_ID}/export", "GET"),
        (f"/api/v1/analytics/events/{EVENT_ID}/report", "GET"),
        (
            f"/api/v1/analytics/compare?event_a={EVENT_ID}&event_b={EVENT_ID_B}",
            "GET",
        ),
    ]

    @pytest.mark.parametrize("url,method", endpoints)
    def test_requires_auth(self, client, url, method):
        response = getattr(client, method.lower())(url)
        assert response.status_code == 401


# ── Organizer overview ───────────────────────────────────────────────────


class TestOrganizerOverview:
    @patch("app.api.analytics.get_admin_client")
    def test_organizer_overview_empty(self, mock_admin, organizer_client):
        mock_admin.return_value = _build_admin_client()

        response = organizer_client.get("/api/v1/analytics/overview/organizer")
        assert response.status_code == 200
        data = response.json()
        assert data["total_events"] == 0
        assert data["total_attendees"] == 0
        assert data["total_recognitions"] == 0
        assert data["events"] == []

    @patch("app.api.analytics.get_admin_client")
    def test_organizer_overview_with_events(self, mock_admin, organizer_client):
        mock_admin.return_value = _build_admin_client(
            events=[
                {
                    "event_id": EVENT_ID,
                    "name": "Test Event",
                    "created_by": ORGANIZER_ID,
                    "starts_at": "2026-01-15T10:00:00+00:00",
                    "ends_at": "2026-01-15T18:00:00+00:00",
                    "location": "Room 101",
                    "is_active": True,
                }
            ]
        )

        response = organizer_client.get("/api/v1/analytics/overview/organizer")
        assert response.status_code == 200
        data = response.json()
        assert data["total_events"] == 1
        assert len(data["events"]) == 1
        assert data["events"][0]["name"] == "Test Event"


# ── Attendee overview ────────────────────────────────────────────────────


class TestAttendeeOverview:
    @patch("app.api.analytics.get_admin_client")
    def test_attendee_overview_empty(self, mock_admin, attendee_client):
        mock_admin.return_value = _build_admin_client()

        response = attendee_client.get("/api/v1/analytics/overview/attendee")
        assert response.status_code == 200
        data = response.json()
        assert data["total_events"] == 0
        assert data["total_people_met"] == 0
        assert data["events"] == []


# ── Event analytics (organizer) ──────────────────────────────────────────


class TestEventAnalyticsOrganizer:
    @patch("app.api.analytics.get_admin_client")
    def test_attendee_cannot_access_organizer_analytics(self, mock_admin, attendee_client):
        mock_client = _build_admin_client(
            events=[{"event_id": EVENT_ID, "created_by": ORGANIZER_ID}]
        )
        mock_admin.return_value = mock_client

        response = attendee_client.get(f"/api/v1/analytics/events/{EVENT_ID}/organizer")
        assert response.status_code == 403

    @patch("app.api.analytics.get_admin_client")
    def test_organizer_gets_full_analytics(self, mock_admin, organizer_client):
        mock_client = _build_admin_client(
            events=[
                {
                    "event_id": EVENT_ID,
                    "name": "Test Event",
                    "created_by": ORGANIZER_ID,
                    "starts_at": "2026-01-15T10:00:00+00:00",
                    "ends_at": "2026-01-15T18:00:00+00:00",
                    "location": "Room 101",
                    "is_active": True,
                    "indexing_status": "completed",
                }
            ]
        )
        mock_admin.return_value = mock_client

        response = organizer_client.get(f"/api/v1/analytics/events/{EVENT_ID}/organizer")
        assert response.status_code == 200
        data = response.json()
        assert data["event_id"] == EVENT_ID
        assert "consent_breakdown" in data
        assert "recognition_timeline" in data
        assert "top_recognized" in data


# ── Event analytics (attendee) ───────────────────────────────────────────


class TestEventAnalyticsAttendee:
    @patch("app.api.analytics.get_admin_client")
    def test_non_member_cannot_view_attendee_analytics(self, mock_admin, attendee_client):
        mock_client = MagicMock()
        membership_q = MagicMock()
        membership_q.select.return_value = membership_q
        membership_q.eq.return_value = membership_q

        membership_resp = MagicMock()
        membership_resp.data = []
        membership_resp.count = 0
        membership_q.execute.return_value = membership_resp

        mock_client.table.return_value = membership_q
        mock_admin.return_value = mock_client

        response = attendee_client.get(f"/api/v1/analytics/events/{EVENT_ID}/attendee")
        assert response.status_code == 403

    @patch("app.api.analytics.get_admin_client")
    def test_member_gets_attendee_analytics(self, mock_admin, attendee_client):
        mock_client = MagicMock()
        call_count = {"n": 0}

        def table_side_effect(name):
            call_count["n"] += 1
            mock_q = MagicMock()
            resp = MagicMock()

            if name == "event_memberships":
                if call_count["n"] == 1:
                    resp.count = 1
                    resp.data = [{"user_id": ATTENDEE_ID}]
                else:
                    resp.data = [{"user_id": ATTENDEE_ID}]
                    resp.count = 1
            elif name == "events":
                resp.data = [
                    {
                        "event_id": EVENT_ID,
                        "name": "Test Event",
                        "starts_at": "2026-01-15T10:00:00+00:00",
                        "ends_at": "2026-01-15T18:00:00+00:00",
                        "location": "Room 101",
                    }
                ]
                resp.count = 1
            elif name == "recognition_logs":
                resp.data = []
                resp.count = 0
            else:
                resp.data = []
                resp.count = 0

            return _make_chainable(mock_q, resp)

        mock_client.table = table_side_effect
        mock_admin.return_value = mock_client

        response = attendee_client.get(f"/api/v1/analytics/events/{EVENT_ID}/attendee")
        assert response.status_code == 200
        data = response.json()
        assert data["event_id"] == EVENT_ID
        assert "your_recognitions" in data
        assert "people_you_met" in data


# ── Live status (organizer only) ─────────────────────────────────────────


class TestLiveEventStatus:
    @patch("app.api.analytics.get_admin_client")
    def test_attendee_blocked_from_live_status(self, mock_admin, attendee_client):
        mock_client = _build_admin_client(
            events=[{"event_id": EVENT_ID, "created_by": ORGANIZER_ID}]
        )
        mock_admin.return_value = mock_client

        response = attendee_client.get(f"/api/v1/analytics/events/{EVENT_ID}/live")
        assert response.status_code == 403

    @patch("app.api.analytics.get_admin_client")
    def test_organizer_gets_live_status(self, mock_admin, organizer_client):
        mock_client = _build_admin_client(
            events=[
                {
                    "event_id": EVENT_ID,
                    "name": "Live Event",
                    "created_by": ORGANIZER_ID,
                }
            ]
        )
        mock_admin.return_value = mock_client

        response = organizer_client.get(f"/api/v1/analytics/events/{EVENT_ID}/live")
        assert response.status_code == 200
        data = response.json()
        assert data["event_id"] == EVENT_ID
        assert "recognitions_last_5min" in data
        assert "active_observers" in data


# ── CSV export (organizer only) ──────────────────────────────────────────


class TestCSVExport:
    @patch("app.api.analytics.get_admin_client")
    def test_attendee_blocked_from_export(self, mock_admin, attendee_client):
        mock_client = _build_admin_client(
            events=[{"event_id": EVENT_ID, "created_by": ORGANIZER_ID}]
        )
        mock_admin.return_value = mock_client

        response = attendee_client.get(f"/api/v1/analytics/events/{EVENT_ID}/export")
        assert response.status_code == 403

    @patch("app.api.analytics.get_admin_client")
    def test_organizer_gets_csv(self, mock_admin, organizer_client):
        mock_client = _build_admin_client(
            events=[
                {
                    "event_id": EVENT_ID,
                    "created_by": ORGANIZER_ID,
                    "name": "Test",
                }
            ]
        )
        mock_admin.return_value = mock_client

        response = organizer_client.get(f"/api/v1/analytics/events/{EVENT_ID}/export")
        assert response.status_code == 200
        assert "text/csv" in response.headers["content-type"]
        assert "user_id" in response.text


# ── Event comparison (organizer only) ────────────────────────────────────


class TestEventComparison:
    @patch("app.api.analytics.get_admin_client")
    def test_non_organizer_blocked_from_compare(self, mock_admin, attendee_client):
        mock_client = _build_admin_client(
            events=[
                {"event_id": EVENT_ID, "created_by": ORGANIZER_ID},
                {"event_id": EVENT_ID_B, "created_by": ORGANIZER_ID},
            ]
        )
        mock_admin.return_value = mock_client

        response = attendee_client.get(
            f"/api/v1/analytics/compare?event_a={EVENT_ID}&event_b={EVENT_ID_B}"
        )
        assert response.status_code == 403


# ── Post-event report (attendee) ────────────────────────────────────────


class TestPostEventReport:
    @patch("app.api.analytics.get_admin_client")
    def test_non_member_blocked_from_report(self, mock_admin, attendee_client):
        mock_client = MagicMock()
        membership_q = MagicMock()
        membership_q.select.return_value = membership_q
        membership_q.eq.return_value = membership_q

        membership_resp = MagicMock()
        membership_resp.data = []
        membership_resp.count = 0
        membership_q.execute.return_value = membership_resp

        mock_client.table.return_value = membership_q
        mock_admin.return_value = mock_client

        response = attendee_client.get(f"/api/v1/analytics/events/{EVENT_ID}/report")
        assert response.status_code == 403

    @patch("app.api.analytics.get_admin_client")
    def test_member_gets_report(self, mock_admin, attendee_client):
        mock_client = MagicMock()
        call_count = {"n": 0}

        def table_side_effect(name):
            call_count["n"] += 1
            mock_q = MagicMock()
            resp = MagicMock()

            if name == "event_memberships":
                if call_count["n"] == 1:
                    resp.count = 1
                    resp.data = [{"user_id": ATTENDEE_ID}]
                else:
                    resp.data = [{"user_id": ATTENDEE_ID}]
                    resp.count = 1
            elif name == "events":
                resp.data = [
                    {
                        "event_id": EVENT_ID,
                        "name": "Test Event",
                        "starts_at": "2026-01-15T10:00:00+00:00",
                    }
                ]
                resp.count = 1
            elif name == "recognition_logs":
                resp.data = []
                resp.count = 0
            else:
                resp.data = []
                resp.count = 0

            return _make_chainable(mock_q, resp)

        mock_client.table = table_side_effect
        mock_admin.return_value = mock_client

        response = attendee_client.get(f"/api/v1/analytics/events/{EVENT_ID}/report")
        assert response.status_code == 200
        data = response.json()
        assert data["event_id"] == EVENT_ID
        assert "networking_score" in data
        assert "connections" in data


# ── Schema validation ────────────────────────────────────────────────────


class TestSchemaValidation:
    def test_time_series_bucket(self):
        from app.schemas.analytics import TimeSeriesBucket

        bucket = TimeSeriesBucket(
            timestamp=datetime(2026, 1, 15, 10, 0, 0, tzinfo=timezone.utc), count=5
        )
        assert bucket.count == 5

    def test_consent_breakdown_defaults(self):
        from app.schemas.analytics import ConsentBreakdown

        cb = ConsentBreakdown()
        assert cb.recognition_opted_in == 0
        assert cb.display_opted_out == 0

    def test_event_quick_stats(self):
        from app.schemas.analytics import EventQuickStats

        stats = EventQuickStats(
            event_id=UUID(EVENT_ID),
            name="Test",
            member_count=10,
            recognition_count=5,
            consent_rate=80.0,
        )
        assert stats.member_count == 10

    def test_attendee_event_analytics(self):
        from app.schemas.analytics import AttendeeEventAnalytics

        analytics = AttendeeEventAnalytics(
            event_id=UUID(EVENT_ID),
            name="Test",
            your_recognitions=3,
            unique_people_you_met=2,
        )
        assert analytics.your_recognitions == 3

    def test_post_event_report_networking_score_capped(self):
        from app.schemas.analytics import PostEventReport

        report = PostEventReport(
            event_id=UUID(EVENT_ID),
            event_name="Test",
            networking_score=100,
        )
        assert report.networking_score <= 100

    def test_live_event_status(self):
        from app.schemas.analytics import LiveEventStatus

        status = LiveEventStatus(
            event_id=UUID(EVENT_ID),
            name="Live Test",
            current_members=20,
            recognitions_last_5min=5,
        )
        assert status.current_members == 20

    def test_attendee_overview(self):
        from app.schemas.analytics import AttendeeOverview

        overview = AttendeeOverview(
            total_events=3,
            total_people_met=15,
            total_recognitions=8,
        )
        assert overview.total_people_met == 15
