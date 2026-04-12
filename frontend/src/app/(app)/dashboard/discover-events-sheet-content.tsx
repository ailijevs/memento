"use client";

import { type EventResponse } from "@/lib/api";
import { CalendarDays, Loader2, MapPin, Search, UserPlus } from "lucide-react";

export interface DiscoverEventItem {
  event: EventResponse;
}

interface DiscoverEventsSheetContentProps {
  loading: boolean;
  searchText: string;
  onSearchTextChange: (value: string) => void;
  events: DiscoverEventItem[];
  joiningEventId: string | null;
  onJoinEvent: (event: EventResponse) => void;
}

export function DiscoverEventsSheetContent({
  loading,
  searchText,
  onSearchTextChange,
  events,
  joiningEventId,
  onJoinEvent,
}: DiscoverEventsSheetContentProps) {
  const hasQuery = searchText.trim().length > 0;

  return (
    <div className="min-h-0 flex-1 flex flex-col">
      <div
        className="mb-3 flex items-center gap-2 rounded-full px-3"
        style={{
          background: "oklch(1 0 0 / 4%)",
          border: "1px solid oklch(1 0 0 / 10%)",
        }}
      >
        <Search className="h-3.5 w-3.5 text-white/35" />
        <input
          value={searchText}
          onChange={(event) => onSearchTextChange(event.target.value)}
          placeholder="Search new events"
          className="h-9 w-full bg-transparent text-[13px] text-white outline-none placeholder:text-white/35"
        />
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain pr-1 pb-2">
        {loading ? (
          <div className="flex items-center justify-center py-10">
            <Loader2 className="h-5 w-5 animate-spin text-white/45" />
          </div>
        ) : events.length === 0 ? (
          <div
            className="rounded-3xl px-5 py-8 text-center"
            style={{
              background: "oklch(1 0 0 / 4%)",
              border: "1px solid oklch(1 0 0 / 8%)",
            }}
          >
            <p className="text-[16px] text-white/75">
              {hasQuery ? "No new events found" : "Search for events"}
            </p>
            <p className="mt-1 text-[13px] text-white/35">
              {hasQuery ? "Try another search term." : "Start typing to discover events."}
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {events.map(({ event }) => {

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
                  </div>

                  <div className="mt-3">
                    <button
                      onClick={() => onJoinEvent(event)}
                      disabled={joiningEventId === event.event_id}
                      className="inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-[11px] font-medium uppercase tracking-[0.1em] text-white/80 transition-transform active:scale-95 disabled:opacity-55"
                      style={{
                        background: "oklch(1 0 0 / 5%)",
                        border: "1px solid oklch(1 0 0 / 11%)",
                      }}
                    >
                      {joiningEventId === event.event_id ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      ) : (
                        <UserPlus className="h-3.5 w-3.5" />
                      )}
                      {joiningEventId === event.event_id ? "Joining" : "Join Event"}
                    </button>
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
