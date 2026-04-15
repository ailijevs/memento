"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import {
  api,
  type EventAnalytics,
  type AttendeeEventAnalytics,
  type LiveEventStatus,
  type PostEventReport,
  type TopRecognizedUser,
} from "@/lib/api";
import { Aurora } from "@/components/aurora";
import {
  ArrowLeft,
  BarChart3,
  CalendarDays,
  ChevronRight,
  Clock,
  Download,
  Eye,
  Handshake,
  Loader2,
  MapPin,
  Radio,
  TrendingUp,
  Trophy,
  Users,
} from "lucide-react";

type ViewMode = "organizer" | "attendee";

export default function EventAnalyticsPage() {
  const router = useRouter();
  const params = useParams();
  const eventId = params.eventId as string;

  const [loading, setLoading] = useState(true);
  const [viewMode, setViewMode] = useState<ViewMode>("attendee");
  const [organizerData, setOrganizerData] = useState<EventAnalytics | null>(null);
  const [attendeeData, setAttendeeData] = useState<AttendeeEventAnalytics | null>(null);
  const [liveStatus, setLiveStatus] = useState<LiveEventStatus | null>(null);
  const [liveLoading, setLiveLoading] = useState(false);
  const [report, setReport] = useState<PostEventReport | null>(null);
  const [reportLoading, setReportLoading] = useState(false);
  const [showLive, setShowLive] = useState(false);
  const [showReport, setShowReport] = useState(false);

  useEffect(() => {
    async function load() {
      const supabase = createClient();
      const {
        data: { session },
      } = await supabase.auth.getSession();

      if (!session) {
        setLoading(false);
        return;
      }

      api.setToken(session.access_token);

      const [orgResult, attResult] = await Promise.allSettled([
        api.getEventAnalyticsOrganizer(eventId),
        api.getEventAnalyticsAttendee(eventId),
      ]);

      if (orgResult.status === "fulfilled") {
        setOrganizerData(orgResult.value);
        setViewMode("organizer");
      }
      if (attResult.status === "fulfilled") {
        setAttendeeData(attResult.value);
        if (orgResult.status !== "fulfilled") {
          setViewMode("attendee");
        }
      }

      setLoading(false);
    }

    void load();
  }, [eventId]);

  async function loadLiveStatus() {
    setLiveLoading(true);
    setShowLive(true);
    try {
      const status = await api.getLiveEventStatus(eventId);
      setLiveStatus(status);
    } catch {
      setLiveStatus(null);
    } finally {
      setLiveLoading(false);
    }
  }

  async function loadReport() {
    setReportLoading(true);
    setShowReport(true);
    try {
      const r = await api.getPostEventReport(eventId);
      setReport(r);
    } catch {
      setReport(null);
    } finally {
      setReportLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="flex h-dvh items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-white/40" />
      </div>
    );
  }

  const eventName = organizerData?.name ?? attendeeData?.name ?? "Event";

  return (
    <div className="relative flex min-h-dvh flex-col">
      <div className="absolute inset-0" style={{ opacity: 0.42 }}>
        <Aurora className="h-full w-full" mode="focused" />
      </div>
      <div
        className="pointer-events-none absolute inset-0"
        style={{
          background: "linear-gradient(to bottom, transparent 18%, oklch(0.07 0.015 270) 52%)",
        }}
      />

      <div className="relative z-10 px-6 pt-14 pb-4">
        <button
          onClick={() => router.push("/analytics")}
          className="mb-3 flex items-center gap-1 text-[12px] text-white/40 transition-colors hover:text-white/60"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Back to Analytics
        </button>

        <h1
          className="text-white"
          style={{
            fontFamily: "var(--font-serif)",
            fontSize: 26,
            fontWeight: 400,
            letterSpacing: "-0.02em",
          }}
        >
          {eventName}
        </h1>

        {organizerData ? (
          <div
            className="mt-4 grid grid-cols-2 gap-2 rounded-full p-1"
            style={{
              background: "oklch(1 0 0 / 4%)",
              border: "1px solid oklch(1 0 0 / 10%)",
            }}
          >
            <button
              onClick={() => setViewMode("organizer")}
              className="flex items-center justify-center gap-2 rounded-full px-3 py-2 text-[11px] font-medium uppercase tracking-[0.1em] transition-transform active:scale-95"
              style={
                viewMode === "organizer"
                  ? {
                      background: "oklch(0.23 0.1 35 / 62%)",
                      border: "1px solid oklch(0.62 0.16 35 / 35%)",
                      color: "oklch(0.94 0.01 250)",
                    }
                  : { color: "oklch(0.87 0.01 250 / 55%)" }
              }
            >
              <BarChart3 className="h-3.5 w-3.5" />
              Organizer View
            </button>
            <button
              onClick={() => setViewMode("attendee")}
              className="flex items-center justify-center gap-2 rounded-full px-3 py-2 text-[11px] font-medium uppercase tracking-[0.1em] transition-transform active:scale-95"
              style={
                viewMode === "attendee"
                  ? {
                      background: "oklch(0.23 0.1 215 / 62%)",
                      border: "1px solid oklch(0.6 0.17 215 / 35%)",
                      color: "oklch(0.94 0.01 250)",
                    }
                  : { color: "oklch(0.87 0.01 250 / 55%)" }
              }
            >
              <Handshake className="h-3.5 w-3.5" />
              My Stats
            </button>
          </div>
        ) : null}
      </div>

      <div className="relative z-10 flex-1 overflow-y-auto px-6 pb-24">
        {viewMode === "organizer" && organizerData ? (
          <OrganizerEventView
            data={organizerData}
            onOpenLive={() => void loadLiveStatus()}
            showLive={showLive}
            liveLoading={liveLoading}
            liveStatus={liveStatus}
          />
        ) : attendeeData ? (
          <AttendeeEventView
            data={attendeeData}
            onOpenReport={() => void loadReport()}
            showReport={showReport}
            reportLoading={reportLoading}
            report={report}
          />
        ) : (
          <div className="mt-8 text-center text-[13px] text-white/40">
            No analytics data available for this event.
          </div>
        )}
      </div>
    </div>
  );
}

function SmallStat({
  label,
  value,
  icon: Icon,
}: {
  label: string;
  value: string | number;
  icon: React.ElementType;
}) {
  return (
    <div
      className="rounded-2xl p-3"
      style={{
        background: "oklch(1 0 0 / 4%)",
        border: "1px solid oklch(1 0 0 / 8%)",
      }}
    >
      <div className="flex items-center gap-1.5 text-white/40">
        <Icon className="h-3 w-3" />
        <span className="text-[9px] font-medium uppercase tracking-[0.1em]">{label}</span>
      </div>
      <p className="mt-1.5 text-[22px] font-light tracking-tight text-white/90">{value}</p>
    </div>
  );
}

function PersonRow({ person }: { person: TopRecognizedUser }) {
  return (
    <div
      className="flex items-center gap-3 rounded-xl p-3"
      style={{
        background: "oklch(1 0 0 / 3%)",
        border: "1px solid oklch(1 0 0 / 6%)",
      }}
    >
      <div className="flex h-9 w-9 items-center justify-center rounded-full bg-white/10 text-[13px] font-medium text-white/60">
        {person.full_name ? person.full_name.charAt(0).toUpperCase() : "?"}
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate text-[13px] font-medium text-white/80">
          {person.full_name ?? "Unknown"}
        </p>
        <p className="text-[11px] text-white/35">
          {person.times_recognized} recognition{person.times_recognized !== 1 ? "s" : ""}
        </p>
      </div>
    </div>
  );
}

function OrganizerEventView({
  data,
  onOpenLive,
  showLive,
  liveLoading,
  liveStatus,
}: {
  data: EventAnalytics;
  onOpenLive: () => void;
  showLive: boolean;
  liveLoading: boolean;
  liveStatus: LiveEventStatus | null;
}) {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-3">
        <SmallStat label="Members" value={data.total_members} icon={Users} />
        <SmallStat label="Recognitions" value={data.total_recognitions} icon={Eye} />
        <SmallStat label="Unique Recognized" value={data.unique_recognized} icon={Handshake} />
        <SmallStat label="Success Rate" value={`${data.success_rate}%`} icon={TrendingUp} />
      </div>

      {data.peak_hour ? (
        <div
          className="flex items-center gap-2 rounded-2xl p-3 text-[12px] text-white/50"
          style={{
            background: "oklch(1 0 0 / 3%)",
            border: "1px solid oklch(1 0 0 / 6%)",
          }}
        >
          <Clock className="h-3.5 w-3.5" />
          Peak hour: <span className="font-medium text-white/70">{data.peak_hour}</span>
        </div>
      ) : null}

      <section>
        <h2 className="mb-3 text-[12px] font-medium uppercase tracking-[0.1em] text-white/50">
          Consent Breakdown
        </h2>
        <div className="grid grid-cols-2 gap-3">
          <div
            className="rounded-2xl p-3"
            style={{
              background: "oklch(1 0 0 / 3%)",
              border: "1px solid oklch(1 0 0 / 6%)",
            }}
          >
            <p className="text-[10px] font-medium uppercase tracking-[0.1em] text-white/40">
              Recognition
            </p>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="text-[20px] font-light text-green-400/80">
                {data.consent_breakdown.recognition_opted_in}
              </span>
              <span className="text-[11px] text-white/30">opted in</span>
            </div>
            <div className="mt-1 flex items-baseline gap-2">
              <span className="text-[16px] font-light text-red-400/60">
                {data.consent_breakdown.recognition_opted_out}
              </span>
              <span className="text-[11px] text-white/30">opted out</span>
            </div>
          </div>
          <div
            className="rounded-2xl p-3"
            style={{
              background: "oklch(1 0 0 / 3%)",
              border: "1px solid oklch(1 0 0 / 6%)",
            }}
          >
            <p className="text-[10px] font-medium uppercase tracking-[0.1em] text-white/40">
              Profile Display
            </p>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="text-[20px] font-light text-green-400/80">
                {data.consent_breakdown.display_opted_in}
              </span>
              <span className="text-[11px] text-white/30">opted in</span>
            </div>
            <div className="mt-1 flex items-baseline gap-2">
              <span className="text-[16px] font-light text-red-400/60">
                {data.consent_breakdown.display_opted_out}
              </span>
              <span className="text-[11px] text-white/30">opted out</span>
            </div>
          </div>
        </div>
      </section>

      {data.top_recognized.length > 0 ? (
        <section>
          <h2 className="mb-3 text-[12px] font-medium uppercase tracking-[0.1em] text-white/50">
            Most Recognized
          </h2>
          <div className="space-y-2">
            {data.top_recognized.map((person) => (
              <PersonRow key={person.user_id} person={person} />
            ))}
          </div>
        </section>
      ) : null}

      {data.recognition_timeline.length > 0 ? (
        <section>
          <h2 className="mb-3 text-[12px] font-medium uppercase tracking-[0.1em] text-white/50">
            Recognition Activity
          </h2>
          <div className="flex items-end gap-1" style={{ height: 80 }}>
            {data.recognition_timeline.map((bucket, i) => {
              const maxCount = Math.max(...data.recognition_timeline.map((b) => b.count));
              const height = maxCount > 0 ? (bucket.count / maxCount) * 100 : 0;
              return (
                <div key={i} className="flex flex-1 flex-col items-center gap-1">
                  <div
                    className="w-full rounded-t"
                    style={{
                      height: `${Math.max(height, 4)}%`,
                      background: "oklch(0.6 0.17 215 / 60%)",
                    }}
                  />
                </div>
              );
            })}
          </div>
        </section>
      ) : null}

      <button
        onClick={onOpenLive}
        className="flex w-full items-center justify-between rounded-2xl p-4 text-left transition-transform active:scale-[0.98]"
        style={{
          background: "oklch(0.2 0.08 35 / 40%)",
          border: "1px solid oklch(0.5 0.15 35 / 30%)",
        }}
      >
        <div className="flex items-center gap-2">
          <Radio className="h-4 w-4 text-orange-400/80" />
          <span className="text-[13px] font-medium text-white/80">Live Monitor</span>
        </div>
        <ChevronRight className="h-4 w-4 text-white/30" />
      </button>

      {showLive ? (
        <section>
          {liveLoading ? (
            <div className="flex items-center justify-center py-4">
              <Loader2 className="h-5 w-5 animate-spin text-white/40" />
            </div>
          ) : liveStatus ? (
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <SmallStat
                  label="Last 5 min"
                  value={liveStatus.recognitions_last_5min}
                  icon={Radio}
                />
                <SmallStat
                  label="Active Observers"
                  value={liveStatus.active_observers}
                  icon={Eye}
                />
              </div>
              {liveStatus.recent_matches.length > 0 ? (
                <div>
                  <h3 className="mb-2 text-[11px] font-medium uppercase tracking-[0.1em] text-white/40">
                    Recent Matches
                  </h3>
                  <div className="space-y-2">
                    {liveStatus.recent_matches.map((person) => (
                      <PersonRow key={person.user_id} person={person} />
                    ))}
                  </div>
                </div>
              ) : null}
            </div>
          ) : (
            <p className="text-center text-[12px] text-white/40">
              Could not load live status.
            </p>
          )}
        </section>
      ) : null}
    </div>
  );
}

function AttendeeEventView({
  data,
  onOpenReport,
  showReport,
  reportLoading,
  report,
}: {
  data: AttendeeEventAnalytics;
  onOpenReport: () => void;
  showReport: boolean;
  reportLoading: boolean;
  report: PostEventReport | null;
}) {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-3 gap-3">
        <SmallStat label="Recognitions" value={data.your_recognitions} icon={Eye} />
        <SmallStat label="People Met" value={data.unique_people_you_met} icon={Handshake} />
        <SmallStat label="Attendees" value={data.total_members} icon={Users} />
      </div>

      {data.people_you_met.length > 0 ? (
        <section>
          <h2 className="mb-3 text-[12px] font-medium uppercase tracking-[0.1em] text-white/50">
            People You Met
          </h2>
          <div className="space-y-2">
            {data.people_you_met.map((person) => (
              <PersonRow key={person.user_id} person={person} />
            ))}
          </div>
        </section>
      ) : (
        <div className="mt-4 text-center text-[13px] text-white/40">
          No connections recorded yet. Use the glasses to recognize people at this event.
        </div>
      )}

      {data.your_recognition_timeline.length > 0 ? (
        <section>
          <h2 className="mb-3 text-[12px] font-medium uppercase tracking-[0.1em] text-white/50">
            Your Activity
          </h2>
          <div className="flex items-end gap-1" style={{ height: 60 }}>
            {data.your_recognition_timeline.map((bucket, i) => {
              const maxCount = Math.max(
                ...data.your_recognition_timeline.map((b) => b.count)
              );
              const height = maxCount > 0 ? (bucket.count / maxCount) * 100 : 0;
              return (
                <div key={i} className="flex flex-1 flex-col items-center">
                  <div
                    className="w-full rounded-t"
                    style={{
                      height: `${Math.max(height, 4)}%`,
                      background: "oklch(0.6 0.17 215 / 60%)",
                    }}
                  />
                </div>
              );
            })}
          </div>
        </section>
      ) : null}

      <button
        onClick={onOpenReport}
        className="flex w-full items-center justify-between rounded-2xl p-4 text-left transition-transform active:scale-[0.98]"
        style={{
          background: "oklch(0.2 0.08 215 / 40%)",
          border: "1px solid oklch(0.5 0.15 215 / 30%)",
        }}
      >
        <div className="flex items-center gap-2">
          <Trophy className="h-4 w-4 text-blue-400/80" />
          <span className="text-[13px] font-medium text-white/80">Networking Report</span>
        </div>
        <ChevronRight className="h-4 w-4 text-white/30" />
      </button>

      {showReport ? (
        <section>
          {reportLoading ? (
            <div className="flex items-center justify-center py-4">
              <Loader2 className="h-5 w-5 animate-spin text-white/40" />
            </div>
          ) : report ? (
            <div className="space-y-4">
              <div
                className="rounded-2xl p-5 text-center"
                style={{
                  background: "oklch(1 0 0 / 4%)",
                  border: "1px solid oklch(1 0 0 / 8%)",
                }}
              >
                <p className="text-[10px] font-medium uppercase tracking-[0.1em] text-white/40">
                  Networking Score
                </p>
                <p className="mt-2 text-[48px] font-light tracking-tight text-white/90">
                  {report.networking_score}
                </p>
                <p className="text-[12px] text-white/40">out of 100</p>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <SmallStat
                  label="People Met"
                  value={report.people_you_met}
                  icon={Handshake}
                />
                <SmallStat
                  label="Recognized"
                  value={report.times_you_were_recognized}
                  icon={Eye}
                />
                <SmallStat
                  label="Attendees"
                  value={report.total_attendees}
                  icon={Users}
                />
              </div>

              {report.connections.length > 0 ? (
                <div>
                  <h3 className="mb-2 text-[11px] font-medium uppercase tracking-[0.1em] text-white/40">
                    Your Connections
                  </h3>
                  <div className="space-y-2">
                    {report.connections.map((person) => (
                      <PersonRow key={person.user_id} person={person} />
                    ))}
                  </div>
                </div>
              ) : null}
            </div>
          ) : (
            <p className="text-center text-[12px] text-white/40">
              Could not load networking report.
            </p>
          )}
        </section>
      ) : null}
    </div>
  );
}
