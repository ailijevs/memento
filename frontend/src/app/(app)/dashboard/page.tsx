"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import {
  api,
  isApiErrorWithStatus,
  type ConsentResponse,
  type EventResponse,
  type ProfileDirectoryResponse,
} from "@/lib/api";
import { Aurora } from "@/components/aurora";
import { ModalBottomSheet } from "@/components/modal-bottom-sheet";
import { ConfirmationDialog } from "@/components/confirmation-dialog";
import { AttendeeContent, AttendeeControls, type AttendeeEventItem } from "./attendee-dashboard";
import { DiscoverEventsSheetContent, type DiscoverEventItem } from "./discover-events-sheet-content";
import { EventDetailSheetContent } from "./event-detail-sheet-content";
import { OrganizerContent, OrganizerControls } from "./organizer-dashboard";
import { RsvpListSheetContent } from "./rsvp-list-sheet-content";
import { EventConsentsSheetContent } from "./event-consents-sheet-content";
import { getCachedEventConsent, setCachedEventConsent } from "@/lib/consent-cache";
import {
  CreateEventSheetContent,
  EditEventSheetContent,
  type CreateEventInput,
  type EditEventInput,
} from "./create-event-sheet-content";
import { CalendarDays, Loader2, LogOut, Plus, UserMinus } from "lucide-react";

type DashboardTab = "attendee" | "organizer";

export default function DashboardPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [currentUserId, setCurrentUserId] = useState<string | null>(null);
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
  const [editingEvent, setEditingEvent] = useState<EventResponse | null>(null);
  const [updatingEvent, setUpdatingEvent] = useState(false);
  const [deletingOrganizedEventId, setDeletingOrganizedEventId] = useState<string | null>(null);
  const [archivingOrganizedEventId, setArchivingOrganizedEventId] = useState<string | null>(null);
  const [unarchivingOrganizedEventId, setUnarchivingOrganizedEventId] = useState<string | null>(null);
  const [joiningDiscoverEventId, setJoiningDiscoverEventId] = useState<string | null>(null);
  const [leavingEventId, setLeavingEventId] = useState<string | null>(null);
  const [confirmLeaveEvent, setConfirmLeaveEvent] = useState<EventResponse | null>(null);
  const [openEventMenuId, setOpenEventMenuId] = useState<string | null>(null);
  const [confirmingSignOut, setConfirmingSignOut] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [detailEvent, setDetailEvent] = useState<EventResponse | null>(null);
  const [isRsvpListOpen, setIsRsvpListOpen] = useState(false);
  const [rsvpListLoading, setRsvpListLoading] = useState(false);
  const [rsvpListEventName, setRsvpListEventName] = useState<string>("");
  const [rsvpListData, setRsvpListData] = useState<ProfileDirectoryResponse>({
    entries: [],
    total_count: 0,
    hidden_count: 0,
  });
  const [showRsvpConsentOffNotice, setShowRsvpConsentOffNotice] = useState(false);
  const [isEditConsentsOpen, setIsEditConsentsOpen] = useState(false);
  const [editingConsentsEvent, setEditingConsentsEvent] = useState<EventResponse | null>(null);
  const [consentsLoading, setConsentsLoading] = useState(false);
  const [consentsSaving, setConsentsSaving] = useState(false);
  const [editingConsent, setEditingConsent] = useState<ConsentResponse | null>(null);
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

      setCurrentUserId(session.user.id);
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
        const { message: registrationClosesMessage, isClosingSoon } =
          formatRegistrationCloseMessage(startsAt, now);
        return {
          event,
          canStillJoin: Number.isFinite(startsAt) && startsAt - now >= 20 * 60 * 1000,
          registrationClosesMessage,
          isClosingSoon,
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

  function handleEditEventRequest(event: EventResponse) {
    setEditingEvent(event);
  }

  async function handleUpdateEvent(input: EditEventInput) {
    if (!editingEvent) {
      return;
    }
    setUpdatingEvent(true);
    try {
      const updatedEvent = await api.updateEvent(editingEvent.event_id, input);
      setOrganizedEvents((previous) =>
        previous.map((existing) => (existing.event_id === updatedEvent.event_id ? updatedEvent : existing))
      );
      setEditingEvent(null);
    } catch (error) {
      console.error("Failed to update event:", error);
      throw error;
    } finally {
      setUpdatingEvent(false);
    }
  }

  async function handleDeleteOrganizedEvent(event: EventResponse) {
    setDeletingOrganizedEventId(event.event_id);
    setActionError(null);
    try {
      await api.deleteEvent(event.event_id);
      setOrganizedEvents((previous) => previous.filter((existing) => existing.event_id !== event.event_id));
    } catch (error) {
      console.error("Failed to delete event:", error);
      if (isApiErrorWithStatus(error, 409)) {
        setActionError(error.message || "Event indexing is in progress. Please retry in a few seconds.");
      } else {
        setActionError("Could not delete event right now. Please try again.");
      }
    } finally {
      setDeletingOrganizedEventId(null);
    }
  }

  async function handleArchiveOrganizedEvent(event: EventResponse) {
    setArchivingOrganizedEventId(event.event_id);
    try {
      const updated = await api.updateEvent(event.event_id, { is_active: false });
      setOrganizedEvents((previous) =>
        previous.map((existing) => (existing.event_id === event.event_id ? updated : existing))
      );
    } catch (error) {
      console.error("Failed to archive event:", error);
    } finally {
      setArchivingOrganizedEventId(null);
    }
  }

  async function handleUnarchiveOrganizedEvent(event: EventResponse) {
    setUnarchivingOrganizedEventId(event.event_id);
    try {
      const updated = await api.updateEvent(event.event_id, { is_active: true });
      setOrganizedEvents((previous) =>
        previous.map((existing) => (existing.event_id === event.event_id ? updated : existing))
      );
    } catch (error) {
      console.error("Failed to unarchive event:", error);
    } finally {
      setUnarchivingOrganizedEventId(null);
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

  function handleViewEventDetail(event: EventResponse) {
    setDetailEvent(event);
  }

  function handleStartRecognition(event: EventResponse) {
    const params = new URLSearchParams({ event_id: event.event_id });
    router.push(`/recognition?${params.toString()}`);
  }

  async function handleLeaveEvent(event: EventResponse) {
    setOpenEventMenuId(null);
    setLeavingEventId(event.event_id);
    setActionError(null);
    try {
      await api.leaveEvent(event.event_id);
      setMyEvents((previous) => previous.filter((existing) => existing.event_id !== event.event_id));
    } catch (error) {
      console.error("Failed to leave event:", error);
      if (isApiErrorWithStatus(error, 409)) {
        setActionError(error.message || "Event indexing is in progress. Please retry in a few seconds.");
      } else {
        setActionError("Could not leave event right now. Please try again.");
      }
    } finally {
      setLeavingEventId(null);
    }
  }

  async function handleConfirmLeaveEvent() {
    if (!confirmLeaveEvent) {
      return;
    }
    await handleLeaveEvent(confirmLeaveEvent);
    setConfirmLeaveEvent(null);
  }

  async function handleViewRsvpList(event: EventResponse) {
    setOpenEventMenuId(null);
    setRsvpListEventName(event.name);
    setIsRsvpListOpen(true);
    setRsvpListLoading(true);
    setRsvpListData({
      entries: [],
      total_count: 0,
      hidden_count: 0,
    });
    setShowRsvpConsentOffNotice(false);
    try {
      let consent = getCachedEventConsent(event.event_id);
      if (!consent) {
        try {
          consent = await api.getMyEventConsent(event.event_id);
          setCachedEventConsent(event.event_id, consent);
        } catch {
          consent = null;
        }
      }

      const isCreator = Boolean(currentUserId && currentUserId === event.created_by);
      setShowRsvpConsentOffNotice(Boolean(!isCreator && consent && !consent.allow_profile_display));

      const data = await api.getEventDirectory(event.event_id);
      setRsvpListData(data);
    } catch (error) {
      console.error("Failed to load RSVP list:", error);
      setRsvpListData({
        entries: [],
        total_count: 0,
        hidden_count: 0,
      });
      setActionError("Could not load RSVP list right now. Please try again.");
    } finally {
      setRsvpListLoading(false);
    }
  }

  async function handleEditConsents(event: EventResponse) {
    setOpenEventMenuId(null);
    setEditingConsentsEvent(event);
    setIsEditConsentsOpen(true);
    setConsentsLoading(true);
    setActionError(null);

    try {
      const consent = await api.getMyEventConsent(event.event_id);
      setEditingConsent(consent);
      setCachedEventConsent(event.event_id, consent);
    } catch (error) {
      console.error("Failed to load event consents:", error);
      setEditingConsent(null);
      setActionError("Could not load event consent settings right now. Please try again.");
    } finally {
      setConsentsLoading(false);
    }
  }

  async function handleConsentUpdate(
    eventId: string,
    patch: {
      allow_profile_display?: boolean;
      allow_recognition?: boolean;
    },
  ) {
    setConsentsSaving(true);
    setActionError(null);
    try {
      const updated = await api.updateMyEventConsent(eventId, patch);
      setEditingConsent(updated);
      setCachedEventConsent(eventId, updated);
    } catch (error) {
      console.error("Failed to update event consent:", error);
      if (error instanceof Error) {
        setActionError(error.message);
      } else {
        setActionError("Could not update event consent right now. Please try again.");
      }
    } finally {
      setConsentsSaving(false);
    }
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
        {actionError ? (
          <div
            className="mb-3 rounded-2xl px-3 py-2 text-[12px] text-amber-200/90"
            style={{
              background: "oklch(0.3 0.09 70 / 22%)",
              border: "1px solid oklch(0.72 0.14 70 / 38%)",
            }}
          >
            {actionError}
          </div>
        ) : null}

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
          <OrganizerContent
            events={organizedEvents}
            formatEventDate={formatEventDate}
            deletingEventId={deletingOrganizedEventId}
            archivingEventId={archivingOrganizedEventId}
            unarchivingEventId={unarchivingOrganizedEventId}
            onViewEventDetail={handleViewEventDetail}
            onEditEventRequest={handleEditEventRequest}
            onViewRsvpList={(event) => void handleViewRsvpList(event)}
            onArchiveEvent={handleArchiveOrganizedEvent}
            onUnarchiveEvent={handleUnarchiveOrganizedEvent}
            onDeleteEvent={handleDeleteOrganizedEvent}
          />
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
            onViewEventDetail={handleViewEventDetail}
            onViewRsvpList={(event) => void handleViewRsvpList(event)}
            onEditConsents={(event) => void handleEditConsents(event)}
            onLeaveEvent={(event) => {
              setOpenEventMenuId(null);
              setConfirmLeaveEvent(event);
            }}
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
          onViewEventDetail={handleViewEventDetail}
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

      <ModalBottomSheet
        isOpen={Boolean(editingEvent)}
        onClose={() => {
          if (!updatingEvent) {
            setEditingEvent(null);
          }
        }}
        title="Edit Event"
      >
        {editingEvent ? (
          <EditEventSheetContent
            isSubmitting={updatingEvent}
            initialValues={editingEvent}
            onSubmit={handleUpdateEvent}
          />
        ) : null}
      </ModalBottomSheet>

      <ModalBottomSheet
        isOpen={Boolean(detailEvent)}
        onClose={() => setDetailEvent(null)}
        title="Event Details"
      >
        {detailEvent ? (
          <EventDetailSheetContent
            event={detailEvent}
            formatEventDate={formatEventDate}
          />
        ) : null}
      </ModalBottomSheet>

      <ModalBottomSheet
        isOpen={isRsvpListOpen}
        onClose={() => setIsRsvpListOpen(false)}
        title={rsvpListEventName ? `RSVP List · ${rsvpListEventName}` : "RSVP List"}
      >
        <RsvpListSheetContent
          loading={rsvpListLoading}
          entries={rsvpListData.entries}
          totalCount={rsvpListData.total_count}
          hiddenCount={rsvpListData.hidden_count}
          showConsentOffNotice={showRsvpConsentOffNotice}
        />
      </ModalBottomSheet>

      <ModalBottomSheet
        isOpen={isEditConsentsOpen}
        onClose={() => {
          if (!consentsSaving) {
            setIsEditConsentsOpen(false);
            setEditingConsentsEvent(null);
            setEditingConsent(null);
          }
        }}
        title={editingConsentsEvent ? `Edit Consents · ${editingConsentsEvent.name}` : "Edit Consents"}
      >
        <EventConsentsSheetContent
          loading={consentsLoading}
          saving={consentsSaving}
          consent={editingConsent}
          onToggleProfileDisplay={(next) => {
            if (!editingConsentsEvent) return;
            void handleConsentUpdate(editingConsentsEvent.event_id, {
              allow_profile_display: next,
            });
          }}
          onToggleRecognition={(next) => {
            if (!editingConsentsEvent) return;
            void handleConsentUpdate(editingConsentsEvent.event_id, {
              allow_recognition: next,
            });
          }}
          onGrantAll={() => {
            if (!editingConsentsEvent) return;
            void handleConsentUpdate(editingConsentsEvent.event_id, {
              allow_profile_display: true,
              allow_recognition: true,
            });
          }}
          onRevokeAll={() => {
            if (!editingConsentsEvent) return;
            void handleConsentUpdate(editingConsentsEvent.event_id, {
              allow_profile_display: false,
              allow_recognition: false,
            });
          }}
        />
      </ModalBottomSheet>

      <ConfirmationDialog
        open={Boolean(confirmLeaveEvent)}
        title="Leave Event?"
        message={
          confirmLeaveEvent
            ? `You will leave ${confirmLeaveEvent.name} and lose access to this event.`
            : "You will leave this event."
        }
        confirmLabel="Leave"
        onConfirm={() => void handleConfirmLeaveEvent()}
        onCancel={() => setConfirmLeaveEvent(null)}
        confirmIcon={
          confirmLeaveEvent && leavingEventId === confirmLeaveEvent.event_id ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <UserMinus className="h-3.5 w-3.5" />
          )
        }
        confirmDisabled={Boolean(confirmLeaveEvent && leavingEventId === confirmLeaveEvent.event_id)}
      />
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

function formatRegistrationCloseMessage(
  startsAtMs: number,
  nowMs: number,
): { message: string; isClosingSoon: boolean } {
  if (!Number.isFinite(startsAtMs)) {
    return { message: "Registration close time unavailable", isClosingSoon: false };
  }

  const closesAtMs = startsAtMs - 20 * 60 * 1000;
  const remainingMs = closesAtMs - nowMs;

  if (remainingMs > 0 && remainingMs <= 5 * 60 * 1000) {
    const remainingMinutes = Math.max(1, Math.ceil(remainingMs / 60000));
    return {
      message: `Registration closes in ${remainingMinutes} minute${remainingMinutes === 1 ? "" : "s"}`,
      isClosingSoon: true,
    };
  }

  const closesAt = new Date(closesAtMs);
  return {
    message: `Registration closes at ${new Intl.DateTimeFormat("en-US", {
      hour: "numeric",
      minute: "2-digit",
      hour12: true,
    }).format(closesAt)}`,
    isClosingSoon: false,
  };
}
