"use client";

import { useEffect, useRef, useState } from "react";
import { type EventResponse } from "@/lib/api";
import { ConfirmationDialog } from "@/components/confirmation-dialog";
import {
  Archive,
  CalendarDays,
  Loader2,
  MapPin,
  MoreHorizontal,
  Pencil,
  Plus,
  Trash2,
  Undo2,
  Users,
} from "lucide-react";

interface OrganizerControlsProps {
  onCreateEvent: () => void;
}

export function OrganizerControls({ onCreateEvent }: OrganizerControlsProps) {
  return (
    <div className="flex w-full justify-center">
      <button
        onClick={onCreateEvent}
        className="flex items-center gap-2 rounded-full px-3 py-2 text-[11px] font-medium uppercase tracking-[0.1em] text-white/75 transition-transform active:scale-95"
        style={{
          background: "oklch(0.22 0.11 215 / 55%)",
          border: "1px solid oklch(0.6 0.17 215 / 30%)",
        }}
      >
        <Plus className="h-3.5 w-3.5" />
        Create Event
      </button>
    </div>
  );
}

interface OrganizerContentProps {
  events: EventResponse[];
  formatEventDate: (value: string) => string;
  deletingEventId: string | null;
  archivingEventId: string | null;
  unarchivingEventId: string | null;
  onEditEventRequest: (event: EventResponse) => void;
  onViewRsvpList: (event: EventResponse) => void;
  onArchiveEvent: (event: EventResponse) => Promise<void>;
  onUnarchiveEvent: (event: EventResponse) => Promise<void>;
  onDeleteEvent: (event: EventResponse) => Promise<void>;
}

export function OrganizerContent({
  events,
  formatEventDate,
  deletingEventId,
  archivingEventId,
  unarchivingEventId,
  onEditEventRequest,
  onViewRsvpList,
  onArchiveEvent,
  onUnarchiveEvent,
  onDeleteEvent,
}: OrganizerContentProps) {
  const [openEventMenuId, setOpenEventMenuId] = useState<string | null>(null);
  const [confirmArchiveEvent, setConfirmArchiveEvent] = useState<EventResponse | null>(null);
  const [confirmDeleteEvent, setConfirmDeleteEvent] = useState<EventResponse | null>(null);
  const openMenuContainerRef = useRef<HTMLDivElement | null>(null);

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

  const sorted = [...events].sort((a, b) => {
    const left = a.starts_at ? Date.parse(a.starts_at) : Number.POSITIVE_INFINITY;
    const right = b.starts_at ? Date.parse(b.starts_at) : Number.POSITIVE_INFINITY;
    return left - right;
  });

  const activeEvents = sorted.filter((event) => event.is_active);
  const inactiveEvents = sorted.filter((event) => !event.is_active);

  function handleEditEvent(event: EventResponse) {
    setOpenEventMenuId(null);
    onEditEventRequest(event);
  }

  function handleArchiveEventClick(event: EventResponse) {
    setOpenEventMenuId(null);
    setConfirmArchiveEvent(event);
  }

  function handleDeleteEventClick(event: EventResponse) {
    setOpenEventMenuId(null);
    setConfirmDeleteEvent(event);
  }

  async function handleConfirmDelete() {
    if (!confirmDeleteEvent) {
      return;
    }
    await onDeleteEvent(confirmDeleteEvent);
    setConfirmDeleteEvent(null);
  }

  async function handleConfirmArchive() {
    if (!confirmArchiveEvent) {
      return;
    }
    await onArchiveEvent(confirmArchiveEvent);
    setConfirmArchiveEvent(null);
  }

  async function handleUnarchiveEvent(event: EventResponse) {
    setOpenEventMenuId(null);
    await onUnarchiveEvent(event);
  }

  return (
    <div className="space-y-5">
      <section>
        <h2 className="mb-2 text-[12px] font-medium uppercase tracking-[0.1em] text-white/50">
          Active Events
        </h2>
        {activeEvents.length === 0 ? (
          <div
            className="rounded-3xl px-5 py-6 text-center"
            style={{
              background: "oklch(1 0 0 / 4%)",
              border: "1px solid oklch(1 0 0 / 8%)",
            }}
          >
            <p className="text-[14px] text-white/65">No active events</p>
          </div>
        ) : (
          <div className="space-y-3">
            {activeEvents.map((event) => (
              <article
                key={event.event_id}
                className="rounded-3xl p-4"
                style={{
                  background: "oklch(1 0 0 / 4%)",
                  border: "1px solid oklch(1 0 0 / 10%)",
                }}
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h3 className="text-[17px] font-medium text-white/90">{event.name}</h3>
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
                        setOpenEventMenuId((current) => (current === event.event_id ? null : event.event_id))
                      }
                      className="inline-flex items-center rounded-full p-1.5 text-white/70 transition-transform active:scale-95"
                      style={{
                        background: "oklch(1 0 0 / 5%)",
                        border: "1px solid oklch(1 0 0 / 11%)",
                      }}
                      aria-label="Organizer event actions"
                    >
                      <MoreHorizontal className="h-4 w-4" />
                    </button>

                    {openEventMenuId === event.event_id ? (
                      <div
                        className="absolute right-0 z-30 mt-2 w-44 rounded-2xl p-1"
                        style={{
                          background: "oklch(0.12 0.02 265)",
                          border: "1px solid oklch(1 0 0 / 12%)",
                        }}
                      >
                        <button
                          onClick={() => handleEditEvent(event)}
                          className="flex w-full items-center gap-2 rounded-xl px-2.5 py-2 text-left text-[11px] font-medium uppercase tracking-[0.08em] text-white/80 transition-all duration-150 hover:bg-white/5 active:scale-[0.99] active:bg-white/15"
                        >
                          <Pencil className="h-3.5 w-3.5" />
                          Edit Event
                        </button>
                        <button
                          onClick={() => {
                            setOpenEventMenuId(null);
                            onViewRsvpList(event);
                          }}
                          className="flex w-full items-center gap-2 rounded-xl px-2.5 py-2 text-left text-[11px] font-medium uppercase tracking-[0.08em] text-white/80 transition-all duration-150 hover:bg-white/5 active:scale-[0.99] active:bg-white/15"
                        >
                          <Users className="h-3.5 w-3.5" />
                          RSVP List
                        </button>
                        <button
                          onClick={() => handleArchiveEventClick(event)}
                          className="flex w-full items-center gap-2 rounded-xl px-2.5 py-2 text-left text-[11px] font-medium uppercase tracking-[0.08em] text-white/80 transition-all duration-150 hover:bg-white/5 active:scale-[0.99] active:bg-white/15"
                        >
                          <Archive className="h-3.5 w-3.5" />
                          Archive Event
                        </button>
                        <button
                          onClick={() => handleDeleteEventClick(event)}
                          className="flex w-full items-center gap-2 rounded-xl px-2.5 py-2 text-left text-[11px] font-medium uppercase tracking-[0.08em] text-white/80 transition-all duration-150 hover:bg-white/5 active:scale-[0.99] active:bg-white/15"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                          Delete Event
                        </button>
                      </div>
                    ) : null}
                  </div>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>

      {inactiveEvents.length > 0 ? (
        <section className="mt-2">
          <h2 className="mb-2 text-[12px] font-medium uppercase tracking-[0.1em] text-white/50">
            Inactive Events
          </h2>
          <div className="space-y-3">
            {inactiveEvents.map((event) => (
              <article
                key={event.event_id}
                className="rounded-3xl p-4"
                style={{
                  background: "oklch(1 0 0 / 4%)",
                  border: "1px solid oklch(1 0 0 / 10%)",
                }}
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h3 className="text-[17px] font-medium text-white/90">{event.name}</h3>
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
                        setOpenEventMenuId((current) => (current === event.event_id ? null : event.event_id))
                      }
                      className="inline-flex items-center rounded-full p-1.5 text-white/70 transition-transform active:scale-95"
                      style={{
                        background: "oklch(1 0 0 / 5%)",
                        border: "1px solid oklch(1 0 0 / 11%)",
                      }}
                      aria-label="Organizer event actions"
                    >
                      <MoreHorizontal className="h-4 w-4" />
                    </button>

                    {openEventMenuId === event.event_id ? (
                      <div
                        className="absolute right-0 z-30 mt-2 w-44 rounded-2xl p-1"
                        style={{
                          background: "oklch(0.12 0.02 265)",
                          border: "1px solid oklch(1 0 0 / 12%)",
                        }}
                      >
                        <button
                          onClick={() => handleEditEvent(event)}
                          className="flex w-full items-center gap-2 rounded-xl px-2.5 py-2 text-left text-[11px] font-medium uppercase tracking-[0.08em] text-white/80 transition-all duration-150 hover:bg-white/5 active:scale-[0.99] active:bg-white/15"
                        >
                          <Pencil className="h-3.5 w-3.5" />
                          Edit Event
                        </button>
                        <button
                          onClick={() => {
                            setOpenEventMenuId(null);
                            onViewRsvpList(event);
                          }}
                          className="flex w-full items-center gap-2 rounded-xl px-2.5 py-2 text-left text-[11px] font-medium uppercase tracking-[0.08em] text-white/80 transition-all duration-150 hover:bg-white/5 active:scale-[0.99] active:bg-white/15"
                        >
                          <Users className="h-3.5 w-3.5" />
                          RSVP List
                        </button>
                        <button
                          onClick={() => void handleUnarchiveEvent(event)}
                          disabled={unarchivingEventId === event.event_id}
                          className="flex w-full items-center gap-2 rounded-xl px-2.5 py-2 text-left text-[11px] font-medium uppercase tracking-[0.08em] text-white/80 transition-all duration-150 hover:bg-white/5 active:scale-[0.99] active:bg-white/15 disabled:opacity-55"
                        >
                          {unarchivingEventId === event.event_id ? (
                            <Loader2 className="h-3.5 w-3.5 animate-spin" />
                          ) : (
                            <Undo2 className="h-3.5 w-3.5" />
                          )}
                          {unarchivingEventId === event.event_id ? "Unarchiving" : "Unarchive Event"}
                        </button>
                        <button
                          onClick={() => handleDeleteEventClick(event)}
                          className="flex w-full items-center gap-2 rounded-xl px-2.5 py-2 text-left text-[11px] font-medium uppercase tracking-[0.08em] text-white/80 transition-all duration-150 hover:bg-white/5 active:scale-[0.99] active:bg-white/15"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                          Delete Event
                        </button>
                      </div>
                    ) : null}
                  </div>
                </div>
              </article>
            ))}
          </div>
        </section>
      ) : null}

      <ConfirmationDialog
        open={Boolean(confirmArchiveEvent)}
        title="Archive Event?"
        message={
          confirmArchiveEvent
            ? `This will hide "${confirmArchiveEvent.name}" from active events.`
            : "This will hide this event from active events."
        }
        confirmLabel="Archive"
        onConfirm={() => void handleConfirmArchive()}
        onCancel={() => setConfirmArchiveEvent(null)}
        confirmIcon={
          confirmArchiveEvent && archivingEventId === confirmArchiveEvent.event_id ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <Archive className="h-3.5 w-3.5" />
          )
        }
        confirmDisabled={Boolean(confirmArchiveEvent && archivingEventId === confirmArchiveEvent.event_id)}
      />

      <ConfirmationDialog
        open={Boolean(confirmDeleteEvent)}
        title="Delete Event?"
        message={
          confirmDeleteEvent
            ? `This will permanently delete "${confirmDeleteEvent.name}".`
            : "This will permanently delete this event."
        }
        confirmLabel="Delete"
        onConfirm={() => void handleConfirmDelete()}
        onCancel={() => setConfirmDeleteEvent(null)}
        confirmIcon={
          confirmDeleteEvent && deletingEventId === confirmDeleteEvent.event_id ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <Trash2 className="h-3.5 w-3.5" />
          )
        }
        confirmDisabled={Boolean(confirmDeleteEvent && deletingEventId === confirmDeleteEvent.event_id)}
      />
    </div>
  );
}
