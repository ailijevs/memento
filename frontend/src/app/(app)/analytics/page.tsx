"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import {
  api,
  type OrganizerOverview,
  type AttendeeOverview,
  type EventQuickStats,
} from "@/lib/api";
import { Aurora } from "@/components/aurora";
import {
  BarChart3,
  CalendarDays,
  Handshake,
  Loader2,
  MapPin,
  Users,
} from "lucide-react";

export default function AnalyticsPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [organizerData, setOrganizerData] = useState<OrganizerOverview | null>(null);
  const [attendeeData, setAttendeeData] = useState<AttendeeOverview | null>(null);
  const [activeView, setActiveView] = useState<"organizer" | "attendee">("attendee");

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

      try {
        const [orgOverview, attOverview] = await Promise.allSettled([
          api.getOrganizerOverview(),
          api.getAttendeeOverview(),
        ]);

        if (orgOverview.status === "fulfilled") {
          setOrganizerData(orgOverview.value);
          if (orgOverview.value.total_events > 0) {
            setActiveView("organizer");
          }
        }
        if (attOverview.status === "fulfilled") {
          setAttendeeData(attOverview.value);
        }
      } finally {
        setLoading(false);
      }
    }

    void load();
  }, []);

  function handleEventClick(event: EventQuickStats) {
    router.push(`/analytics/${event.event_id}`);
  }

  if (loading) {
    return (
      <div className="flex h-dvh items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-white/40" />
      </div>
    );
  }

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
        <h1
          className="text-white"
          style={{
            fontFamily: "var(--font-serif)",
            fontSize: 30,
            fontWeight: 400,
            letterSpacing: "-0.02em",
          }}
        >
          Analytics
        </h1>
        <p className="mt-1 text-[13px] text-white/45">
          Track event performance and your networking activity.
        </p>

        <div
          className="mt-4 grid grid-cols-2 gap-2 rounded-full p-1"
          style={{
            background: "oklch(1 0 0 / 4%)",
            border: "1px solid oklch(1 0 0 / 10%)",
          }}
        >
          <button
            onClick={() => setActiveView("attendee")}
            className="flex items-center justify-center gap-2 rounded-full px-3 py-2 text-[11px] font-medium uppercase tracking-[0.1em] transition-transform active:scale-95"
            style={
              activeView === "attendee"
                ? {
                    background: "oklch(0.23 0.1 215 / 62%)",
                    border: "1px solid oklch(0.6 0.17 215 / 35%)",
                    color: "oklch(0.94 0.01 250)",
                  }
                : { color: "oklch(0.87 0.01 250 / 55%)" }
            }
          >
            <Handshake className="h-3.5 w-3.5" />
            My Networking
          </button>
          <button
            onClick={() => setActiveView("organizer")}
            className="flex items-center justify-center gap-2 rounded-full px-3 py-2 text-[11px] font-medium uppercase tracking-[0.1em] transition-transform active:scale-95"
            style={
              activeView === "organizer"
                ? {
                    background: "oklch(0.23 0.1 35 / 62%)",
                    border: "1px solid oklch(0.62 0.16 35 / 35%)",
                    color: "oklch(0.94 0.01 250)",
                  }
                : { color: "oklch(0.87 0.01 250 / 55%)" }
            }
          >
            <BarChart3 className="h-3.5 w-3.5" />
            Organizer
          </button>
        </div>
      </div>

      <div className="relative z-10 flex-1 overflow-y-auto px-6 pb-24">
        {activeView === "attendee" ? (
          <AttendeeView data={attendeeData} onEventClick={handleEventClick} />
        ) : (
          <OrganizerView data={organizerData} onEventClick={handleEventClick} />
        )}
      </div>
    </div>
  );
}

function StatCard({
  label,
  value,
  icon: Icon,
}: {
  label: string;
  value: string | number;
  icon?: React.ElementType;
}) {
  return (
    <div
      className="flex flex-col items-center justify-between rounded-2xl p-4 text-center"
      style={{
        background: "oklch(1 0 0 / 4%)",
        border: "1px solid oklch(1 0 0 / 8%)",
      }}
    >
      <div className="flex min-h-[32px] items-center justify-center gap-1.5 text-white/40">
        {Icon ? <Icon className="h-3.5 w-3.5 shrink-0" /> : null}
        <span className="text-[10px] font-medium uppercase leading-tight tracking-[0.1em]">{label}</span>
      </div>
      <p className="text-[28px] font-light tracking-tight text-white/90">{value}</p>
    </div>
  );
}

function EventRow({
  event,
  onClick,
  extras,
}: {
  event: EventQuickStats;
  onClick: () => void;
  extras?: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className="w-full rounded-2xl p-4 text-left transition-transform active:scale-[0.98]"
      style={{
        background: "oklch(1 0 0 / 4%)",
        border: "1px solid oklch(1 0 0 / 10%)",
      }}
    >
      <h3 className="text-[15px] font-medium text-white/90">{event.name}</h3>
      <div className="mt-1.5 flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-white/40">
        {event.starts_at ? (
          <span className="inline-flex items-center gap-1">
            <CalendarDays className="h-3 w-3" />
            {formatDate(event.starts_at)}
          </span>
        ) : null}
        {event.location ? (
          <span className="inline-flex items-center gap-1">
            <MapPin className="h-3 w-3" />
            {event.location}
          </span>
        ) : null}
        <span className="inline-flex items-center gap-1">
          <Users className="h-3 w-3" />
          {event.member_count}
        </span>
      </div>
      {extras}
    </button>
  );
}

function AttendeeView({
  data,
  onEventClick,
}: {
  data: AttendeeOverview | null;
  onEventClick: (event: EventQuickStats) => void;
}) {
  if (!data) {
    return (
      <div className="mt-8 text-center text-[13px] text-white/40">
        No networking data available yet.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-3">
        <StatCard label="Events" value={data.total_events} icon={CalendarDays} />
        <StatCard label="People Met" value={data.total_people_met} icon={Handshake} />
      </div>

      {data.events.length > 0 ? (
        <section>
          <h2 className="mb-3 text-[12px] font-medium uppercase tracking-[0.1em] text-white/50">
            Your Events
          </h2>
          <div className="space-y-3">
            {data.events.map((event) => (
              <EventRow
                key={event.event_id}
                event={event}
                onClick={() => onEventClick(event)}
              />
            ))}
          </div>
        </section>
      ) : (
        <div className="mt-4 text-center text-[13px] text-white/40">
          Join events to start tracking your networking.
        </div>
      )}
    </div>
  );
}

function OrganizerView({
  data,
  onEventClick,
}: {
  data: OrganizerOverview | null;
  onEventClick: (event: EventQuickStats) => void;
}) {
  if (!data || data.total_events === 0) {
    return (
      <div className="mt-8 text-center text-[13px] text-white/40">
        Create events from the Dashboard to see organizer analytics.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-3">
        <StatCard label="Events" value={data.total_events} icon={CalendarDays} />
        <StatCard label="Total Attendees" value={data.total_attendees} icon={Users} />
      </div>

      <section>
        <h2 className="mb-3 text-[12px] font-medium uppercase tracking-[0.1em] text-white/50">
          Your Events
        </h2>
        <div className="space-y-3">
          {data.events.map((event) => (
            <EventRow
              key={event.event_id}
              event={event}
              onClick={() => onEventClick(event)}
              extras={
                <div className="mt-2 flex items-center gap-3 text-[10px] text-white/30">
                  <span>Consent: {event.consent_rate}%</span>
                  <span>{event.is_active ? "Active" : "Inactive"}</span>
                </div>
              }
            />
          ))}
        </div>
      </section>
    </div>
  );
}

function formatDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Date TBD";
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(date);
}
