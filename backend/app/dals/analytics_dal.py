"""Data Access Layer for analytics queries."""

import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from app.dals.base_dal import BaseDAL
from app.schemas.analytics import (
    AttendeeEventAnalytics,
    AttendeeExportRow,
    AttendeeOverview,
    ConsentBreakdown,
    EventAnalytics,
    EventComparison,
    EventQuickStats,
    LiveEventStatus,
    OrganizerOverview,
    PostEventReport,
    TimeSeriesBucket,
    TopRecognizedUser,
)
from supabase import Client

logger = logging.getLogger(__name__)


class AnalyticsDAL(BaseDAL):
    """DAL for analytics queries. Uses admin client to bypass RLS."""

    def __init__(self, client: Client):
        super().__init__(client)

    # ── helpers ────────────────────────────────────────────────────────────

    async def _get_member_count(self, event_id: UUID) -> int:
        resp = (
            self.client.table("event_memberships")
            .select("user_id", count="exact", head=True)
            .eq("event_id", str(event_id))
            .execute()
        )
        return int(resp.count or 0)

    async def _get_recognition_count(self, event_id: UUID) -> int:
        resp = (
            self.client.table("recognition_logs")
            .select("id", count="exact", head=True)
            .eq("event_id", str(event_id))
            .execute()
        )
        return int(resp.count or 0)

    async def _get_unique_recognized_count(self, event_id: UUID) -> int:
        resp = (
            self.client.table("recognition_logs")
            .select("recognized_user_id")
            .eq("event_id", str(event_id))
            .execute()
        )
        unique_ids = {row["recognized_user_id"] for row in resp.data}
        return len(unique_ids)

    async def _get_consent_breakdown(self, event_id: UUID) -> ConsentBreakdown:
        resp = (
            self.client.table("event_consents")
            .select("allow_recognition,allow_profile_display")
            .eq("event_id", str(event_id))
            .execute()
        )
        recog_in = len([r for r in resp.data if r.get("allow_recognition")])
        recog_out = len([r for r in resp.data if not r.get("allow_recognition")])
        display_in = len([r for r in resp.data if r.get("allow_profile_display")])
        display_out = len([r for r in resp.data if not r.get("allow_profile_display")])
        return ConsentBreakdown(
            recognition_opted_in=recog_in,
            recognition_opted_out=recog_out,
            display_opted_in=display_in,
            display_opted_out=display_out,
        )

    async def _get_consent_rate(self, event_id: UUID) -> float:
        breakdown = await self._get_consent_breakdown(event_id)
        total = breakdown.recognition_opted_in + breakdown.recognition_opted_out
        if total == 0:
            return 0.0
        return round(breakdown.recognition_opted_in / total * 100, 1)

    async def _get_recognition_timeline(
        self, event_id: UUID, *, hours: int = 24
    ) -> list[TimeSeriesBucket]:
        since = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
        resp = (
            self.client.table("recognition_logs")
            .select("created_at")
            .eq("event_id", str(event_id))
            .gte("created_at", since)
            .order("created_at", desc=False)
            .execute()
        )
        return self._bucket_by_hour(resp.data)

    async def _get_join_timeline(self, event_id: UUID) -> list[TimeSeriesBucket]:
        resp = (
            self.client.table("event_memberships")
            .select("created_at")
            .eq("event_id", str(event_id))
            .order("created_at", desc=False)
            .execute()
        )
        return self._bucket_by_hour(resp.data)

    async def _get_top_recognized(
        self, event_id: UUID, *, limit: int = 10
    ) -> list[TopRecognizedUser]:
        resp = (
            self.client.table("recognition_logs")
            .select("recognized_user_id")
            .eq("event_id", str(event_id))
            .execute()
        )
        counts: dict[str, int] = {}
        for row in resp.data:
            uid = row["recognized_user_id"]
            counts[uid] = counts.get(uid, 0) + 1

        sorted_users = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:limit]
        results: list[TopRecognizedUser] = []

        for user_id, count in sorted_users:
            profile = (
                self.client.table("profiles")
                .select("full_name,photo_path")
                .eq("user_id", user_id)
                .maybe_single()
                .execute()
            )
            results.append(
                TopRecognizedUser(
                    user_id=UUID(user_id),
                    full_name=profile.data.get("full_name") if profile.data else None,
                    photo_path=profile.data.get("photo_path") if profile.data else None,
                    times_recognized=count,
                )
            )
        return results

    async def _get_peak_hour(self, event_id: UUID) -> str | None:
        resp = (
            self.client.table("recognition_logs")
            .select("created_at")
            .eq("event_id", str(event_id))
            .execute()
        )
        if not resp.data:
            return None

        hour_counts: dict[int, int] = {}
        for row in resp.data:
            ts = datetime.fromisoformat(row["created_at"].replace("Z", "+00:00"))
            h = ts.hour
            hour_counts[h] = hour_counts.get(h, 0) + 1

        if not hour_counts:
            return None

        peak = max(hour_counts, key=lambda k: hour_counts[k])
        return f"{peak:02d}:00"

    @staticmethod
    def _bucket_by_hour(rows: list[dict]) -> list[TimeSeriesBucket]:
        """Group rows with a created_at field into hourly buckets."""
        if not rows:
            return []

        buckets: dict[str, int] = {}
        for row in rows:
            ts = datetime.fromisoformat(row["created_at"].replace("Z", "+00:00"))
            key = ts.strftime("%Y-%m-%dT%H:00:00+00:00")
            buckets[key] = buckets.get(key, 0) + 1

        return [
            TimeSeriesBucket(timestamp=datetime.fromisoformat(k), count=v)
            for k, v in sorted(buckets.items())
        ]

    # ── organizer endpoints ───────────────────────────────────────────────

    async def get_organizer_overview(self, user_id: UUID) -> OrganizerOverview:
        """Aggregate stats across all events created by this user."""
        events_resp = (
            self.client.table("events")
            .select("*")
            .eq("created_by", str(user_id))
            .order("starts_at", desc=True)
            .execute()
        )

        event_stats: list[EventQuickStats] = []
        total_attendees = 0
        total_recognitions = 0
        consent_rates: list[float] = []

        for ev in events_resp.data:
            eid = UUID(ev["event_id"])
            members = await self._get_member_count(eid)
            recogs = await self._get_recognition_count(eid)
            cr = await self._get_consent_rate(eid)

            total_attendees += members
            total_recognitions += recogs
            consent_rates.append(cr)

            event_stats.append(
                EventQuickStats(
                    event_id=eid,
                    name=ev["name"],
                    starts_at=ev.get("starts_at"),
                    ends_at=ev.get("ends_at"),
                    location=ev.get("location"),
                    is_active=ev.get("is_active", True),
                    member_count=members,
                    recognition_count=recogs,
                    consent_rate=cr,
                )
            )

        avg_consent = round(sum(consent_rates) / len(consent_rates), 1) if consent_rates else 0.0

        return OrganizerOverview(
            total_events=len(events_resp.data),
            total_attendees=total_attendees,
            total_recognitions=total_recognitions,
            avg_consent_rate=avg_consent,
            events=event_stats,
        )

    async def get_attendee_overview(self, user_id: UUID) -> AttendeeOverview:
        """Aggregate stats across all events this user has joined."""
        memberships_resp = (
            self.client.table("event_memberships")
            .select("event_id")
            .eq("user_id", str(user_id))
            .execute()
        )

        if not memberships_resp.data:
            return AttendeeOverview()

        event_ids = [row["event_id"] for row in memberships_resp.data]
        events_resp = (
            self.client.table("events")
            .select("*")
            .in_("event_id", event_ids)
            .order("starts_at", desc=True)
            .execute()
        )

        event_stats: list[EventQuickStats] = []
        total_recognitions = 0
        all_people_met: set[str] = set()

        for ev in events_resp.data:
            eid = UUID(ev["event_id"])
            members = await self._get_member_count(eid)

            user_recogs_resp = (
                self.client.table("recognition_logs")
                .select("recognized_user_id")
                .eq("event_id", str(eid))
                .eq("observer_user_id", str(user_id))
                .execute()
            )
            recog_count = len(user_recogs_resp.data)
            total_recognitions += recog_count

            for row in user_recogs_resp.data:
                all_people_met.add(row["recognized_user_id"])

            cr = await self._get_consent_rate(eid)

            event_stats.append(
                EventQuickStats(
                    event_id=eid,
                    name=ev["name"],
                    starts_at=ev.get("starts_at"),
                    ends_at=ev.get("ends_at"),
                    location=ev.get("location"),
                    is_active=ev.get("is_active", True),
                    member_count=members,
                    recognition_count=recog_count,
                    consent_rate=cr,
                )
            )

        return AttendeeOverview(
            total_events=len(events_resp.data),
            total_people_met=len(all_people_met),
            total_recognitions=total_recognitions,
            events=event_stats,
        )

    async def get_event_analytics_organizer(self, event_id: UUID) -> EventAnalytics:
        """Full analytics for an event (organizer view)."""
        ev_resp = (
            self.client.table("events")
            .select("*")
            .eq("event_id", str(event_id))
            .maybe_single()
            .execute()
        )
        if not ev_resp.data:
            raise ValueError("Event not found")

        ev = ev_resp.data
        members = await self._get_member_count(event_id)
        recogs = await self._get_recognition_count(event_id)
        unique = await self._get_unique_recognized_count(event_id)
        consent = await self._get_consent_breakdown(event_id)
        timeline = await self._get_recognition_timeline(event_id)
        join_tl = await self._get_join_timeline(event_id)
        top = await self._get_top_recognized(event_id)
        peak = await self._get_peak_hour(event_id)

        return EventAnalytics(
            event_id=event_id,
            name=ev["name"],
            starts_at=ev.get("starts_at"),
            ends_at=ev.get("ends_at"),
            location=ev.get("location"),
            is_active=ev.get("is_active", True),
            indexing_status=ev.get("indexing_status", "pending"),
            total_members=members,
            total_recognitions=recogs,
            unique_recognized=unique,
            peak_hour=peak,
            consent_breakdown=consent,
            recognition_timeline=timeline,
            join_timeline=join_tl,
            top_recognized=top,
        )

    async def get_event_analytics_attendee(
        self, event_id: UUID, user_id: UUID
    ) -> AttendeeEventAnalytics:
        """Attendee-scoped analytics for a single event."""
        ev_resp = (
            self.client.table("events")
            .select("*")
            .eq("event_id", str(event_id))
            .maybe_single()
            .execute()
        )
        if not ev_resp.data:
            raise ValueError("Event not found")

        ev = ev_resp.data
        members = await self._get_member_count(event_id)

        user_recogs_resp = (
            self.client.table("recognition_logs")
            .select("recognized_user_id,created_at")
            .eq("event_id", str(event_id))
            .eq("observer_user_id", str(user_id))
            .order("created_at", desc=False)
            .execute()
        )

        your_recognitions = len(user_recogs_resp.data)
        people_met_ids: set[str] = set()
        for row in user_recogs_resp.data:
            people_met_ids.add(row["recognized_user_id"])

        timeline = self._bucket_by_hour(user_recogs_resp.data)

        people_met: list[TopRecognizedUser] = []
        met_counts: dict[str, int] = {}
        for row in user_recogs_resp.data:
            uid = row["recognized_user_id"]
            met_counts[uid] = met_counts.get(uid, 0) + 1

        for uid, count in sorted(met_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
            profile = (
                self.client.table("profiles")
                .select("full_name,photo_path")
                .eq("user_id", uid)
                .maybe_single()
                .execute()
            )
            people_met.append(
                TopRecognizedUser(
                    user_id=UUID(uid),
                    full_name=profile.data.get("full_name") if profile.data else None,
                    photo_path=profile.data.get("photo_path") if profile.data else None,
                    times_recognized=count,
                )
            )

        return AttendeeEventAnalytics(
            event_id=event_id,
            name=ev["name"],
            starts_at=ev.get("starts_at"),
            ends_at=ev.get("ends_at"),
            location=ev.get("location"),
            total_members=members,
            your_recognitions=your_recognitions,
            unique_people_you_met=len(people_met_ids),
            your_recognition_timeline=timeline,
            people_you_met=people_met,
        )

    async def get_event_comparison(self, event_id_a: UUID, event_id_b: UUID) -> EventComparison:
        """Side-by-side comparison of two events."""

        async def _quick_stats(eid: UUID) -> EventQuickStats:
            ev = (
                self.client.table("events")
                .select("*")
                .eq("event_id", str(eid))
                .maybe_single()
                .execute()
            )
            if not ev.data:
                raise ValueError(f"Event {eid} not found")
            members = await self._get_member_count(eid)
            recogs = await self._get_recognition_count(eid)
            cr = await self._get_consent_rate(eid)
            return EventQuickStats(
                event_id=eid,
                name=ev.data["name"],
                starts_at=ev.data.get("starts_at"),
                ends_at=ev.data.get("ends_at"),
                location=ev.data.get("location"),
                is_active=ev.data.get("is_active", True),
                member_count=members,
                recognition_count=recogs,
                consent_rate=cr,
            )

        return EventComparison(
            event_a=await _quick_stats(event_id_a),
            event_b=await _quick_stats(event_id_b),
        )

    async def get_live_event_status(self, event_id: UUID) -> LiveEventStatus:
        """Real-time status for a live event."""
        ev = (
            self.client.table("events")
            .select("name")
            .eq("event_id", str(event_id))
            .maybe_single()
            .execute()
        )
        if not ev.data:
            raise ValueError("Event not found")

        members = await self._get_member_count(event_id)
        total_recogs = await self._get_recognition_count(event_id)

        five_min_ago = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
        recent_resp = (
            self.client.table("recognition_logs")
            .select("recognized_user_id,observer_user_id")
            .eq("event_id", str(event_id))
            .gte("created_at", five_min_ago)
            .execute()
        )

        active_observers = len(
            {row["observer_user_id"] for row in recent_resp.data if row.get("observer_user_id")}
        )

        recent_match_counts: dict[str, int] = {}
        for row in recent_resp.data:
            uid = row["recognized_user_id"]
            recent_match_counts[uid] = recent_match_counts.get(uid, 0) + 1

        recent_matches: list[TopRecognizedUser] = []
        for uid, count in sorted(recent_match_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
            profile = (
                self.client.table("profiles")
                .select("full_name,photo_path")
                .eq("user_id", uid)
                .maybe_single()
                .execute()
            )
            recent_matches.append(
                TopRecognizedUser(
                    user_id=UUID(uid),
                    full_name=profile.data.get("full_name") if profile.data else None,
                    photo_path=profile.data.get("photo_path") if profile.data else None,
                    times_recognized=count,
                )
            )

        return LiveEventStatus(
            event_id=event_id,
            name=ev.data["name"],
            current_members=members,
            recognitions_last_5min=len(recent_resp.data),
            total_recognitions=total_recogs,
            active_observers=active_observers,
            recent_matches=recent_matches,
        )

    async def get_attendee_export(self, event_id: UUID) -> list[AttendeeExportRow]:
        """Get all attendees with their consent and recognition data for CSV export."""
        members_resp = (
            self.client.table("event_memberships")
            .select("user_id,role,created_at")
            .eq("event_id", str(event_id))
            .order("created_at", desc=False)
            .execute()
        )

        rows: list[AttendeeExportRow] = []
        for m in members_resp.data:
            uid = m["user_id"]

            profile = (
                self.client.table("profiles")
                .select("full_name")
                .eq("user_id", uid)
                .maybe_single()
                .execute()
            )

            consent = (
                self.client.table("event_consents")
                .select("allow_recognition,allow_profile_display")
                .eq("event_id", str(event_id))
                .eq("user_id", uid)
                .maybe_single()
                .execute()
            )

            recog_count_resp = (
                self.client.table("recognition_logs")
                .select("id", count="exact", head=True)
                .eq("event_id", str(event_id))
                .eq("recognized_user_id", uid)
                .execute()
            )

            user_resp = (
                self.client.table("auth.users")
                .select("email")
                .eq("id", uid)
                .maybe_single()
                .execute()
            )
            email = user_resp.data.get("email") if user_resp.data else None

            rows.append(
                AttendeeExportRow(
                    user_id=UUID(uid),
                    full_name=profile.data.get("full_name") if profile.data else None,
                    email=email,
                    role=m.get("role", "member"),
                    allow_recognition=(
                        consent.data.get("allow_recognition", False) if consent.data else False
                    ),
                    allow_profile_display=(
                        consent.data.get("allow_profile_display", False) if consent.data else False
                    ),
                    joined_at=m.get("created_at"),
                    times_recognized=int(recog_count_resp.count or 0),
                )
            )

        return rows

    async def get_post_event_report(self, event_id: UUID, user_id: UUID) -> PostEventReport:
        """Personalized post-event networking report for an attendee."""
        ev = (
            self.client.table("events")
            .select("name,starts_at")
            .eq("event_id", str(event_id))
            .maybe_single()
            .execute()
        )
        if not ev.data:
            raise ValueError("Event not found")

        total_attendees = await self._get_member_count(event_id)

        user_recogs_resp = (
            self.client.table("recognition_logs")
            .select("recognized_user_id")
            .eq("event_id", str(event_id))
            .eq("observer_user_id", str(user_id))
            .execute()
        )

        was_recognized_resp = (
            self.client.table("recognition_logs")
            .select("id", count="exact", head=True)
            .eq("event_id", str(event_id))
            .eq("recognized_user_id", str(user_id))
            .execute()
        )

        met_counts: dict[str, int] = {}
        for row in user_recogs_resp.data:
            uid = row["recognized_user_id"]
            met_counts[uid] = met_counts.get(uid, 0) + 1

        connections: list[TopRecognizedUser] = []
        for uid, count in sorted(met_counts.items(), key=lambda x: x[1], reverse=True):
            profile = (
                self.client.table("profiles")
                .select("full_name,photo_path")
                .eq("user_id", uid)
                .maybe_single()
                .execute()
            )
            connections.append(
                TopRecognizedUser(
                    user_id=UUID(uid),
                    full_name=profile.data.get("full_name") if profile.data else None,
                    photo_path=profile.data.get("photo_path") if profile.data else None,
                    times_recognized=count,
                )
            )

        people_met = len(met_counts)
        times_recognized = int(was_recognized_resp.count or 0)

        connection_names = [c.full_name or "Unknown" for c in connections[:10]]
        score, summary = await self._compute_networking_score(
            event_name=ev.data["name"],
            total_attendees=total_attendees,
            people_met=people_met,
            times_recognized=times_recognized,
            connection_names=connection_names,
        )

        return PostEventReport(
            event_id=event_id,
            event_name=ev.data["name"],
            event_date=ev.data.get("starts_at"),
            total_attendees=total_attendees,
            people_you_met=people_met,
            times_you_were_recognized=times_recognized,
            connections=connections,
            networking_score=score,
            networking_summary=summary,
        )

    # ── AI scoring ─────────────────────────────────────────────────────────

    async def _compute_networking_score(
        self,
        *,
        event_name: str,
        total_attendees: int,
        people_met: int,
        times_recognized: int,
        connection_names: list[str],
    ) -> tuple[int, str | None]:
        """Use OpenAI to compute a networking score (0-100) and a short summary.

        Falls back to a simple ratio-based formula if OpenAI is unavailable.
        """
        from app.config import get_settings

        settings = get_settings()
        if not settings.openai_api_key:
            score = min(100, int((people_met / max(total_attendees - 1, 1)) * 100))
            return score, None

        try:
            import openai

            client = openai.OpenAI(api_key=settings.openai_api_key)

            prompt = (
                f"You are an event networking analyst. Score the "
                f"attendee's networking performance at "
                f'"{event_name}" from 0 to 100 and write a '
                f"1-2 sentence summary.\n\n"
                f"Stats:\n"
                f"- Total attendees: {total_attendees}\n"
                f"- People this person met (recognized): {people_met}\n"
                f"- Times this person was recognized by others: {times_recognized}\n"
                f"- People they connected with: {', '.join(connection_names) or 'none'}\n\n"
                f"Consider: meeting a high percentage of attendees is impressive, being "
                f"recognized by others shows visibility, and diverse connections matter.\n\n"
                f"Respond in exactly this JSON format, nothing else:\n"
                f'{{"score": <int 0-100>, "summary": "<1-2 sentence summary>"}}'
            )

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=150,
            )

            import json

            content = response.choices[0].message.content or ""
            result = json.loads(content)
            score = max(0, min(100, int(result["score"])))
            summary = result.get("summary")
            return score, summary

        except Exception as e:
            logger.warning("OpenAI networking score failed, using fallback: %s", e)
            score = min(100, int((people_met / max(total_attendees - 1, 1)) * 100))
            return score, None

    # ── logging ───────────────────────────────────────────────────────────

    _DEDUP_WINDOW_SECONDS = 60

    async def log_recognition_match(
        self,
        *,
        event_id: UUID | None,
        recognized_user_id: UUID,
        observer_user_id: UUID,
        confidence: float,
    ) -> None:
        """Insert a recognition_logs row, skipping if a duplicate exists within the dedup window.

        The frontend sends frames every ~500ms, so without dedup, staring at
        one person for 10 seconds would create ~20 log rows. This checks for
        a recent log with the same (observer, recognized, event) tuple and
        skips the insert if one exists within the last 60 seconds.
        """
        since = (
            datetime.now(timezone.utc) - timedelta(seconds=self._DEDUP_WINDOW_SECONDS)
        ).isoformat()

        query = (
            self.client.table("recognition_logs")
            .select("id", count="exact", head=True)
            .eq("observer_user_id", str(observer_user_id))
            .eq("recognized_user_id", str(recognized_user_id))
            .gte("created_at", since)
        )
        if event_id is not None:
            query = query.eq("event_id", str(event_id))

        existing = query.execute()
        if existing.count and existing.count > 0:
            return

        insert_data: dict = {
            "recognized_user_id": str(recognized_user_id),
            "observer_user_id": str(observer_user_id),
            "confidence": confidence,
        }
        if event_id is not None:
            insert_data["event_id"] = str(event_id)

        self.client.table("recognition_logs").insert(insert_data).execute()
