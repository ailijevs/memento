"use client";

import { type EventResponse } from "@/lib/api";
import { CalendarDays, MapPin, Plus } from "lucide-react";

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
}

export function OrganizerContent({ events, formatEventDate }: OrganizerContentProps) {
  const sorted = [...events].sort((a, b) => {
    const left = a.starts_at ? Date.parse(a.starts_at) : Number.POSITIVE_INFINITY;
    const right = b.starts_at ? Date.parse(b.starts_at) : Number.POSITIVE_INFINITY;
    return left - right;
  });

  const activeEvents = sorted.filter((event) => event.is_active);
  const inactiveEvents = sorted.filter((event) => !event.is_active);

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
              </article>
            ))}
          </div>
        </section>
      ) : null}
    </div>
  );
}
