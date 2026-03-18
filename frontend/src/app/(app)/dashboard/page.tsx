"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { api, type EventResponse } from "@/lib/api";
import { Aurora } from "@/components/aurora";
import { ModalBottomSheet } from "@/components/modal-bottom-sheet";
import { AttendeeContent, AttendeeControls, type AttendeeEventItem } from "./attendee-dashboard";
import { DiscoverEventsSheetContent, type DiscoverEventItem } from "./discover-events-sheet-content";
import { OrganizerContent, OrganizerControls } from "./organizer-dashboard";
import { CreateEventSheetContent, type CreateEventInput } from "./create-event-sheet-content";
import { CalendarDays, LogOut, Plus } from "lucide-react";

type DashboardTab = "attendee" | "organizer";

export default function DashboardPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [myEvents, setMyEvents] = useState<EventResponse[]>([]);
  const [organizedEvents, setOrganizedEvents] = useState<EventResponse[]>([]);
  const [searchText, setSearchText] = useState("");
  const [activeTab, setActiveTab] = useState<DashboardTab>("attendee");
  const [isDiscoverOpen, setIsDiscoverOpen] = useState(false);
  const [discoverLoading, setDiscoverLoading] = useState(false);
  const [discoverEvents, setDiscoverEvents] = useState<EventResponse[]>([]);
  const [discoverSearchText, setDiscoverSearchText] = useState("");
  const [isCreateEventOpen, setIsCreateEventOpen] = useState(false);
  const [creatingEvent, setCreatingEvent] = useState(false);
  const [joiningDiscoverEventId, setJoiningDiscoverEventId] = useState<string | null>(null);
  const [leavingEventId, setLeavingEventId] = useState<string | null>(null);
  const [openEventMenuId, setOpenEventMenuId] = useState<string | null>(null);
  const [confirmingSignOut, setConfirmingSignOut] = useState(false);
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
        const [events, organized] = await Promise.all([
          api.getMyEvents(),
          api.getMyOrganizedEvents(),
        ]);
        setMyEvents(events);
        setOrganizedEvents(organized);
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

  const attendeeEventItems = useMemo<AttendeeEventItem[]>(() => {
    const now = Date.now();
    return filteredUpcomingEvents.map((event) => {
      const startsAtMs = event.starts_at ? Date.parse(event.starts_at) : Number.NaN;
      return {
        event,
        hasStarted: Number.isFinite(startsAtMs) && startsAtMs <= now,
      };
    });
  }, [filteredUpcomingEvents]);

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
    setIsCreateEventOpen(true);
  }

  async function handleCreateEvent(input: CreateEventInput) {
    setCreatingEvent(true);
    try {
      const createdEvent = await api.createEvent(input);
      setOrganizedEvents((previous) => [createdEvent, ...previous]);
      setIsCreateEventOpen(false);
    } finally {
      setCreatingEvent(false);
    }
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
    <div className="relative flex h-dvh flex-col overflow-hidden">
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
        <div className="mb-4">
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
              Your Lineup
            </h1>
            <p className="mt-1 text-[13px] text-white/45">Check your schedule or find something new.</p>
          </div>
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
          <AttendeeControls
            searchText={searchText}
            onSearchTextChange={setSearchText}
            onOpenDiscover={() => void handleOpenDiscover()}
          />
        ) : (
          <OrganizerControls onCreateEvent={handleCreateEventClick} />
        )}
      </div>

      <div className="relative z-10 flex-1 overflow-y-auto px-6 pb-4">
        {activeTab === "organizer" ? (
          <OrganizerContent events={organizedEvents} formatEventDate={formatEventDate} />
        ) : (
          <AttendeeContent
            loading={loading}
            events={attendeeEventItems}
            openEventMenuId={openEventMenuId}
            openMenuContainerRef={openMenuContainerRef}
            leavingEventId={leavingEventId}
            onToggleEventMenu={(eventId) =>
              setOpenEventMenuId((current) => (current === eventId ? null : eventId))
            }
            onEditConsents={handleEditConsents}
            onLeaveEvent={(event) => void handleLeaveEvent(event)}
            onStartRecognition={handleStartRecognition}
            formatEventDate={formatEventDate}
          />
        )}
        {confirmingSignOut ? (
          <div className="mt-6 mb-2 flex items-center justify-center gap-3">
            <span className="text-[13px] text-white/40">Sign out?</span>
            <button
              onClick={() => void handleSignOut()}
              className="rounded-full px-4 py-1.5 text-[12px] font-medium text-red-400/80 active:text-red-400"
              style={{
                background: "rgba(255,80,80,0.08)",
                border: "1px solid rgba(255,80,80,0.15)",
              }}
            >
              Yes, sign out
            </button>
            <button
              onClick={() => setConfirmingSignOut(false)}
              className="text-[12px] text-white/25 active:text-white/50"
            >
              Cancel
            </button>
          </div>
        ) : (
          <button
            onClick={() => setConfirmingSignOut(true)}
            className="mt-6 mb-2 flex w-full items-center justify-center gap-2 py-2 text-[13px] text-white/25 active:text-white/50"
          >
            <LogOut className="h-3.5 w-3.5" />
            Sign Out
          </button>
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

      <ModalBottomSheet
        isOpen={isCreateEventOpen}
        onClose={() => {
          if (!creatingEvent) {
            setIsCreateEventOpen(false);
          }
        }}
        title="Create Event"
      >
        <CreateEventSheetContent
          isSubmitting={creatingEvent}
          onSubmit={handleCreateEvent}
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
