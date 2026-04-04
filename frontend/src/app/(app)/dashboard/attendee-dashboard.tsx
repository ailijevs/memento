"use client";

import type { RefObject } from "react";
import { type EventResponse } from "@/lib/api";
import { CalendarDays, Loader2, MapPin, MoreHorizontal, ScanFace, Search, ShieldCheck, UserMinus } from "lucide-react";

export interface AttendeeEventItem {
  event: EventResponse;
  hasStarted: boolean;
}

interface AttendeeControlsProps {
  searchText: string;
  onSearchTextChange: (value: string) => void;
  onOpenDiscover: () => void;
}

export function AttendeeControls({
  searchText,
  onSearchTextChange,
  onOpenDiscover,
}: AttendeeControlsProps) {
  return (
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
          onChange={(event) => onSearchTextChange(event.target.value)}
          placeholder="Search your events"
          className="h-9 w-full bg-transparent text-[13px] text-white outline-none placeholder:text-white/35"
        />
      </div>
      <button
        onClick={onOpenDiscover}
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
  );
}

interface AttendeeContentProps {
  loading: boolean;
  events: AttendeeEventItem[];
  openEventMenuId: string | null;
  openMenuContainerRef: RefObject<HTMLDivElement | null>;
  leavingEventId: string | null;
  onToggleEventMenu: (eventId: string) => void;
  onEditConsents: (event: EventResponse) => void;
  onLeaveEvent: (event: EventResponse) => void;
  onStartRecognition: (event: EventResponse) => void;
  formatEventDate: (value: string) => string;
}

export function AttendeeContent({
  loading,
  events,
  openEventMenuId,
  openMenuContainerRef,
  leavingEventId,
  onToggleEventMenu,
  onEditConsents,
  onLeaveEvent,
  onStartRecognition,
  formatEventDate,
}: AttendeeContentProps) {
  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <Loader2 className="h-6 w-6 animate-spin text-white/45" />
      </div>
    );
  }

  if (events.length === 0) {
    return (
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
    );
  }

  return (
    <div className="space-y-3">
      {events.map(({ event, hasStarted }) => {
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
                  onClick={() => onToggleEventMenu(event.event_id)}
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
                      onClick={() => onEditConsents(event)}
                      className="flex w-full items-center gap-2 rounded-xl px-2.5 py-2 text-left text-[11px] font-medium uppercase tracking-[0.08em] text-white/80 transition-all duration-150 hover:bg-white/5 active:scale-[0.99] active:bg-white/15"
                    >
                      <ShieldCheck className="h-3.5 w-3.5" />
                      Edit Consents
                    </button>
                    <button
                      onClick={() => onLeaveEvent(event)}
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
              {hasStarted ? (
                <button
                  onClick={() => onStartRecognition(event)}
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
                <p className="text-[12px] text-white/55">
                  Recognition opens when this event starts
                </p>
              )}
            </div>
          </article>
        );
      })}
    </div>
  );
}
