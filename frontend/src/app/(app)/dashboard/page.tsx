"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { api, type EventResponse } from "@/lib/api";
import { Aurora } from "@/components/aurora";
import { CalendarDays, Loader2, LogOut, MapPin, Plus, ScanFace, Search, UserPlus } from "lucide-react";

export default function DashboardPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [events, setEvents] = useState<EventResponse[]>([]);
  const [joinedEventIds, setJoinedEventIds] = useState<Set<string>>(new Set());
  const [searchText, setSearchText] = useState("");
  const [joiningEventId, setJoiningEventId] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      const supabase = createClient();
      const {
        data: { session },
      } = await supabase.auth.getSession();
      if (!session) {
        accessTokenRef.current = null;
        setLoading(false);
        return;
      }

      accessTokenRef.current = session.access_token;
      api.setToken(session.access_token);
      try {
        const [allEvents, myEvents] = await Promise.all([api.getEvents(), api.getMyEvents()]);
        setEvents(allEvents);
        setJoinedEventIds(new Set(myEvents.map((event) => event.event_id)));
      } finally {
        setLoading(false);
      }
    }

    void load();
  }, []);

  const filteredEvents = useMemo(() => {
    const query = searchText.trim().toLowerCase();
    const sorted = [...events].sort((a, b) => {
      const left = a.starts_at ? Date.parse(a.starts_at) : Number.POSITIVE_INFINITY;
      const right = b.starts_at ? Date.parse(b.starts_at) : Number.POSITIVE_INFINITY;
      return left - right;
    });

    if (!query) {
      return sorted;
    }

    return sorted.filter((event) => {
      const haystack = [event.name, event.location ?? ""].join(" ").toLowerCase();
      return haystack.includes(query);
    });
  }, [events, searchText]);

  const joinedCount = joinedEventIds.size;

  async function handleSignOut() {
    const supabase = createClient();
    await supabase.auth.signOut();
    router.push("/");
    router.refresh();
  }

  async function handleJoin(event: EventResponse) {
    if (joinedEventIds.has(event.event_id)) {
      return;
    }

    setJoiningEventId(event.event_id);
    try {
      await api.joinEvent(event.event_id);
      setJoinedEventIds((previous) => new Set(previous).add(event.event_id));
    } catch (error) {
      console.error("Failed to join event:", error);
    } finally {
      setJoiningEventId(null);
    }
  }

  function handleCreateEventClick() {
    // Intentionally left blank for now.
  }

  function handleStartRecognition(event: EventResponse) {
    const params = new URLSearchParams({ event_id: event.event_id });
    router.push(`/recognition?${params.toString()}`);
  }

  return (
    <div className="relative flex min-h-dvh flex-col overflow-hidden">
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
        <div className="mb-4 flex items-center justify-between">
          <div>
            <h1
              className="text-white"
              style={{
                fontFamily: "var(--font-serif)",
                fontSize: 30,
                fontWeight: 400,
                letterSpacing: "-0.02em",
              }}
            >
              Events
            </h1>
            <p className="mt-1 text-[13px] text-white/45">
              {joinedCount} joined {joinedCount === 1 ? "event" : "events"}
            </p>
          </div>

          <button
            onClick={handleSignOut}
            className="flex h-10 w-10 items-center justify-center rounded-full transition-all active:scale-95"
            style={{
              background: "oklch(1 0 0 / 4%)",
              border: "1px solid oklch(1 0 0 / 10%)",
            }}
            title="Sign out"
          >
            <LogOut className="h-4 w-4 text-white/65" />
          </button>
        </div>

        <div className="mb-3 flex gap-2">
          <button
            onClick={handleCreateEventClick}
            className="flex items-center gap-2 rounded-full px-3 py-2 text-[11px] font-medium uppercase tracking-[0.1em] text-white/75 transition-transform active:scale-95"
            style={{
              background: "oklch(0.22 0.11 215 / 55%)",
              border: "1px solid oklch(0.6 0.17 215 / 30%)",
            }}
          >
            <Plus className="h-3.5 w-3.5" />
            Create Event
          </button>

          <div
            className="flex flex-1 items-center gap-2 rounded-full px-3"
            style={{
              background: "oklch(1 0 0 / 4%)",
              border: "1px solid oklch(1 0 0 / 10%)",
            }}
          >
            <Search className="h-3.5 w-3.5 text-white/35" />
            <input
              value={searchText}
              onChange={(event) => setSearchText(event.target.value)}
              placeholder="Search events"
              className="h-9 w-full bg-transparent text-[13px] text-white outline-none placeholder:text-white/35"
            />
          </div>
        </div>
      </div>

      <div className="relative z-10 flex-1 overflow-y-auto px-6 pb-4">
        {loading ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="h-6 w-6 animate-spin text-white/45" />
          </div>
        ) : filteredEvents.length === 0 ? (
          <div
            className="rounded-3xl px-5 py-8 text-center"
            style={{
              background: "oklch(1 0 0 / 4%)",
              border: "1px solid oklch(1 0 0 / 8%)",
            }}
          >
            <p className="text-[16px] text-white/75">No events found</p>
            <p className="mt-1 text-[13px] text-white/35">Try another search term.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {filteredEvents.map((event) => {
              const isJoined = joinedEventIds.has(event.event_id);
              const isJoining = joiningEventId === event.event_id;
              return (
                <article
                  key={event.event_id}
                  className="rounded-3xl p-4"
                  style={{
                    background: "oklch(1 0 0 / 4%)",
                    border: "1px solid oklch(1 0 0 / 10%)",
                  }}
                >
                  <div className="mb-2 flex items-start justify-between gap-3">
                    <div>
                      <h2 className="text-[17px] font-medium text-white/90">{event.name}</h2>
                      <div className="mt-1 flex flex-wrap gap-2 text-[12px] text-white/45">
                        {event.starts_at ? (
                          <span className="inline-flex items-center gap-1">
                            <CalendarDays className="h-3.5 w-3.5" />
                            {formatEventDate(event.starts_at)}
                          </span>
                        ) : null}
                        {event.location ? (
                          <span className="inline-flex items-center gap-1">
                            <MapPin className="h-3.5 w-3.5" />
                            {event.location}
                          </span>
                        ) : null}
                      </div>
                    </div>

                    {isJoined ? (
                      <span
                        className="rounded-full px-2.5 py-1 text-[10px] font-medium uppercase tracking-[0.08em]"
                        style={{
                          background: "oklch(0.24 0.1 150 / 60%)",
                          color: "oklch(0.82 0.13 150)",
                          border: "1px solid oklch(0.55 0.16 150 / 35%)",
                        }}
                      >
                        Joined
                      </span>
                    ) : null}
                  </div>

                  <div className="mt-3">
                    {isJoined ? (
                      <button
                        onClick={() => handleStartRecognition(event)}
                        className="inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-[11px] font-medium uppercase tracking-[0.1em] text-white/85 transition-transform active:scale-95"
                        style={{
                          background: "oklch(0.22 0.11 25 / 62%)",
                          border: "1px solid oklch(0.58 0.19 25 / 36%)",
                        }}
                      >
                        <ScanFace className="h-3.5 w-3.5" />
                        Start Recognition
                      </button>
                    ) : (
                      <button
                        onClick={() => void handleJoin(event)}
                        disabled={isJoining}
                        className="inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-[11px] font-medium uppercase tracking-[0.1em] text-white/80 transition-transform active:scale-95 disabled:opacity-55"
                        style={{
                          background: "oklch(1 0 0 / 5%)",
                          border: "1px solid oklch(1 0 0 / 11%)",
                        }}
                      >
                        {isJoining ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <UserPlus className="h-3.5 w-3.5" />}
                        {isJoining ? "Joining" : "Join Event"}
                      </button>
                    )}
                  </div>
                </article>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

function formatEventDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "Date TBD";
  }
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(date);
}
