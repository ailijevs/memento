"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { api, type EventResponse } from "@/lib/api";
import { Aurora } from "@/components/aurora";
import { ModalBottomSheet } from "@/components/modal-bottom-sheet";
import { DiscoverEventsSheetContent, type DiscoverEventItem } from "./discover-events-sheet-content";
import { CalendarDays, Loader2, LogOut, MapPin, MoreHorizontal, Plus, ScanFace, Search, ShieldCheck, UserMinus } from "lucide-react";

type DashboardTab = "attendee" | "organizer";

export default function DashboardPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [myEvents, setMyEvents] = useState<EventResponse[]>([]);
  const [searchText, setSearchText] = useState("");
  const [activeTab, setActiveTab] = useState<DashboardTab>("attendee");
  const [isDiscoverOpen, setIsDiscoverOpen] = useState(false);
  const [discoverLoading, setDiscoverLoading] = useState(false);
  const [discoverEvents, setDiscoverEvents] = useState<EventResponse[]>([]);
  const [discoverSearchText, setDiscoverSearchText] = useState("");
  const [joiningDiscoverEventId, setJoiningDiscoverEventId] = useState<string | null>(null);
  const [leavingEventId, setLeavingEventId] = useState<string | null>(null);
  const [openEventMenuId, setOpenEventMenuId] = useState<string | null>(null);
  const openMenuContainerRef = useRef<HTMLDivElement | null>(null);

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
        const events = await api.getMyEvents();
        setMyEvents(events);
      } finally {
        setLoading(false);
      }
    }

    void load();
  }, []);

  useEffect(() => {
    if (!openEventMenuId) {
      return;
    }

    function handlePointerDown(event: MouseEvent | TouchEvent) {
      const target = event.target as Node | null;
      if (!target) {
        return;
      }
      if (openMenuContainerRef.current?.contains(target)) {
        return;
      }
      setOpenEventMenuId(null);
    }

    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("touchstart", handlePointerDown);

    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("touchstart", handlePointerDown);
    };
  }, [openEventMenuId]);

  const upcomingEvents = useMemo(() => {
    const now = Date.now();
    return [...myEvents]
      .filter((event) => {
        const endsAt = event.ends_at ? Date.parse(event.ends_at) : Number.NaN;
        return Number.isFinite(endsAt) ? endsAt >= now : true;
      })
      .sort((a, b) => {
        const left = a.starts_at ? Date.parse(a.starts_at) : Number.POSITIVE_INFINITY;
        const right = b.starts_at ? Date.parse(b.starts_at) : Number.POSITIVE_INFINITY;
        return left - right;
      });
  }, [myEvents]);

  const filteredUpcomingEvents = useMemo(() => {
    return upcomingEvents;
  }, [upcomingEvents]);

  const discoveredUpcomingEvents = useMemo<DiscoverEventItem[]>(() => {
    const query = discoverSearchText.trim().toLowerCase();
    const myEventIds = new Set(myEvents.map((event) => event.event_id));
    const now = Date.now();

    const base = [...discoverEvents]
      .filter((event) => !myEventIds.has(event.event_id))
      .filter((event) => {
        const endsAt = event.ends_at ? Date.parse(event.ends_at) : Number.NaN;
        return Number.isFinite(endsAt) ? endsAt >= now : true;
      })
      .sort((a, b) => {
        const left = a.starts_at ? Date.parse(a.starts_at) : Number.POSITIVE_INFINITY;
        const right = b.starts_at ? Date.parse(b.starts_at) : Number.POSITIVE_INFINITY;
        return left - right;
      });

    if (!query) {
      return [];
    }

    return base
      .filter((event) => {
        const haystack = [event.name, event.location ?? ""].join(" ").toLowerCase();
        return haystack.includes(query);
      })
      .map((event) => {
        const startsAt = Date.parse(event.starts_at ?? "");
        return {
          event,
          canStillJoin: Number.isFinite(startsAt) && startsAt - now >= 30 * 60 * 1000,
        };
      });
  }, [discoverEvents, discoverSearchText, myEvents]);

  async function handleSignOut() {
    const supabase = createClient();
    await supabase.auth.signOut();
    router.push("/");
    router.refresh();
  }

  function handleCreateEventClick() {
    // Intentionally left blank for now.
  }

  async function handleOpenDiscover() {
    setIsDiscoverOpen(true);
    setDiscoverSearchText("");

    setDiscoverLoading(true);
    try {
      const events = await api.getEvents();
      setDiscoverEvents(events);
    } catch (error) {
      console.error("Failed to load discover events:", error);
      setDiscoverEvents([]);
    } finally {
      setDiscoverLoading(false);
    }
  }

  async function handleJoinDiscoverEvent(event: EventResponse) {
    setJoiningDiscoverEventId(event.event_id);
    try {
      await api.joinEvent(event.event_id);
      setMyEvents((previous) => {
        if (previous.some((existing) => existing.event_id === event.event_id)) {
          return previous;
        }
        return [...previous, event];
      });
    } catch (error) {
      console.error("Failed to join event:", error);
    } finally {
      setJoiningDiscoverEventId(null);
    }
  }

  function handleStartRecognition(event: EventResponse) {
    const params = new URLSearchParams({ event_id: event.event_id });
    router.push(`/recognition?${params.toString()}`);
  }

  async function handleLeaveEvent(event: EventResponse) {
    setOpenEventMenuId(null);
    setLeavingEventId(event.event_id);
    try {
      await api.leaveEvent(event.event_id);
      setMyEvents((previous) => previous.filter((existing) => existing.event_id !== event.event_id));
    } catch (error) {
      console.error("Failed to leave event:", error);
    } finally {
      setLeavingEventId(null);
    }
  }

  function handleEditConsents(event: EventResponse) {
    setOpenEventMenuId(null);
    // Intentionally left blank for now.
    void event;
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
              {upcomingEvents.length} upcoming {upcomingEvents.length === 1 ? "event" : "events"}
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

        <div
          className="mb-3 grid grid-cols-2 gap-2 rounded-full p-1"
          style={{
            background: "oklch(1 0 0 / 4%)",
            border: "1px solid oklch(1 0 0 / 10%)",
          }}
        >
          <button
            onClick={() => setActiveTab("attendee")}
            className="flex items-center justify-center gap-2 rounded-full px-3 py-2 text-[11px] font-medium uppercase tracking-[0.1em] transition-transform active:scale-95"
            style={
              activeTab === "attendee"
                ? {
                    background: "oklch(0.23 0.1 215 / 62%)",
                    border: "1px solid oklch(0.6 0.17 215 / 35%)",
                    color: "oklch(0.94 0.01 250)",
                  }
                : { color: "oklch(0.87 0.01 250 / 55%)" }
            }
          >
            <CalendarDays className="h-3.5 w-3.5" />
            Attendee
          </button>
          <button
            onClick={() => setActiveTab("organizer")}
            className="flex items-center justify-center gap-2 rounded-full px-3 py-2 text-[11px] font-medium uppercase tracking-[0.1em] transition-transform active:scale-95"
            style={
              activeTab === "organizer"
                ? {
                    background: "oklch(0.23 0.1 35 / 62%)",
                    border: "1px solid oklch(0.62 0.16 35 / 35%)",
                    color: "oklch(0.94 0.01 250)",
                  }
                : { color: "oklch(0.87 0.01 250 / 55%)" }
            }
          >
            <Plus className="h-3.5 w-3.5" />
            Organizer
          </button>
        </div>

        {activeTab === "attendee" ? (
          <div className="flex items-center gap-2">
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
                placeholder="Search your events"
                className="h-9 w-full bg-transparent text-[13px] text-white outline-none placeholder:text-white/35"
              />
            </div>
            <button
              onClick={() => void handleOpenDiscover()}
              className="shrink-0 flex items-center gap-2 rounded-full px-3 py-2 text-[11px] font-medium uppercase tracking-[0.1em] text-white/75 transition-transform active:scale-95"
              style={{
                background: "oklch(0.22 0.08 190 / 58%)",
                border: "1px solid oklch(0.58 0.12 190 / 32%)",
              }}
            >
              <Search className="h-3.5 w-3.5" />
              Discover Events
            </button>
          </div>
        ) : (
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
        )}
      </div>

      <div className="relative z-10 flex-1 overflow-y-auto px-6 pb-4">
        {activeTab === "organizer" ? (
          <div
            className="rounded-3xl px-5 py-8 text-center"
            style={{
              background: "oklch(1 0 0 / 4%)",
              border: "1px solid oklch(1 0 0 / 8%)",
            }}
          >
            <p className="text-[16px] text-white/75">Organizer tools</p>
            <p className="mt-1 text-[13px] text-white/35">Use the create button above to add a new event. (Coming soon)</p>
          </div>
        ) : loading ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="h-6 w-6 animate-spin text-white/45" />
          </div>
        ) : filteredUpcomingEvents.length === 0 ? (
          <div
            className="rounded-3xl px-5 py-8 text-center"
            style={{
              background: "oklch(1 0 0 / 4%)",
              border: "1px solid oklch(1 0 0 / 8%)",
            }}
          >
            <p className="text-[16px] text-white/75">No upcoming events found</p>
            <p className="mt-1 text-[13px] text-white/35">Try another search term.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {filteredUpcomingEvents.map((event) => {
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

                    <div
                      className="relative"
                      ref={openEventMenuId === event.event_id ? openMenuContainerRef : null}
                    >
                      <button
                        onClick={() =>
                          setOpenEventMenuId((current) =>
                            current === event.event_id ? null : event.event_id,
                          )
                        }
                        className="inline-flex items-center rounded-full p-1.5 text-white/70 transition-transform active:scale-95"
                        style={{
                          background: "oklch(1 0 0 / 5%)",
                          border: "1px solid oklch(1 0 0 / 11%)",
                        }}
                        aria-label="Event actions"
                      >
                        <MoreHorizontal className="h-4 w-4" />
                      </button>

                      {openEventMenuId === event.event_id ? (
                        <div
                          className="absolute right-0 z-30 mt-2 w-40 rounded-2xl p-1"
                          style={{
                            background: "oklch(0.12 0.02 265)",
                            border: "1px solid oklch(1 0 0 / 12%)",
                          }}
                        >
                          <button
                            onClick={() => handleEditConsents(event)}
                            className="flex w-full items-center gap-2 rounded-xl px-2.5 py-2 text-left text-[11px] font-medium uppercase tracking-[0.08em] text-white/80 transition-all duration-150 hover:bg-white/5 active:scale-[0.99] active:bg-white/15"
                          >
                            <ShieldCheck className="h-3.5 w-3.5" />
                            Edit Consents
                          </button>
                          <button
                            onClick={() => void handleLeaveEvent(event)}
                            disabled={leavingEventId === event.event_id}
                            className="flex w-full items-center gap-2 rounded-xl px-2.5 py-2 text-left text-[11px] font-medium uppercase tracking-[0.08em] text-white/80 transition-all duration-150 hover:bg-white/5 active:scale-[0.99] active:bg-white/15 disabled:opacity-55"
                          >
                            {leavingEventId === event.event_id ? (
                              <Loader2 className="h-3.5 w-3.5 animate-spin" />
                            ) : (
                              <UserMinus className="h-3.5 w-3.5" />
                            )}
                            {leavingEventId === event.event_id ? "Leaving" : "Leave Event"}
                          </button>
                        </div>
                      ) : null}
                    </div>
                  </div>

                  <div className="mt-3">
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
                  </div>
                </article>
              );
            })}
          </div>
        )}
      </div>

      <ModalBottomSheet
        isOpen={isDiscoverOpen}
        onClose={() => setIsDiscoverOpen(false)}
        title="Discover Events"
      >
        <DiscoverEventsSheetContent
          loading={discoverLoading}
          searchText={discoverSearchText}
          onSearchTextChange={setDiscoverSearchText}
          events={discoveredUpcomingEvents}
          joiningEventId={joiningDiscoverEventId}
          onJoinEvent={handleJoinDiscoverEvent}
        />
      </ModalBottomSheet>
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
