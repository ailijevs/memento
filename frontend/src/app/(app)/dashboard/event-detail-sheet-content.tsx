"use client";

import { type EventResponse } from "@/lib/api";
import { CalendarDays, Clock, MapPin, Text, Users } from "lucide-react";

interface EventDetailSheetContentProps {
  event: EventResponse;
  formatEventDate: (value: string) => string;
}

export function EventDetailSheetContent({
  event,
  formatEventDate,
}: EventDetailSheetContentProps) {
  return (
    <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain pr-1 pb-2">
      <div className="space-y-5">
        <section>
          <h3
            className="text-white"
            style={{
              fontFamily: "var(--font-serif)",
              fontSize: 24,
              fontWeight: 400,
              letterSpacing: "-0.02em",
            }}
          >
            {event.name}
          </h3>

          {!event.is_active ? (
            <span
              className="mt-2 inline-block rounded-full px-2.5 py-1 text-[10px] font-medium uppercase tracking-[0.1em]"
              style={{
                background: "oklch(0.3 0.06 50 / 45%)",
                border: "1px solid oklch(0.6 0.1 50 / 30%)",
                color: "oklch(0.85 0.06 50)",
              }}
            >
              Inactive
            </span>
          ) : null}
        </section>

        <section className="space-y-3">
          {event.starts_at ? (
            <DetailRow icon={<CalendarDays className="h-4 w-4" />} label="Starts">
              {formatEventDate(event.starts_at)}
            </DetailRow>
          ) : null}

          {event.ends_at ? (
            <DetailRow icon={<Clock className="h-4 w-4" />} label="Ends">
              {formatEventDate(event.ends_at)}
            </DetailRow>
          ) : null}

          {event.location ? (
            <DetailRow icon={<MapPin className="h-4 w-4" />} label="Location">
              {event.location}
            </DetailRow>
          ) : null}

          {event.max_participants != null ? (
            <DetailRow icon={<Users className="h-4 w-4" />} label="Max Participants">
              {event.max_participants.toLocaleString()}
            </DetailRow>
          ) : null}
        </section>

        {event.description ? (
          <section>
            <div className="mb-2 flex items-center gap-2 text-[11px] font-medium uppercase tracking-[0.08em] text-white/50">
              <Text className="h-3.5 w-3.5" />
              Description
            </div>
            <p
              className="whitespace-pre-wrap rounded-2xl px-4 py-3 text-[14px] leading-relaxed text-white/75"
              style={{
                background: "oklch(1 0 0 / 4%)",
                border: "1px solid oklch(1 0 0 / 8%)",
              }}
            >
              {event.description}
            </p>
          </section>
        ) : null}
      </div>
    </div>
  );
}

interface DetailRowProps {
  icon: React.ReactNode;
  label: string;
  children: React.ReactNode;
}

function DetailRow({ icon, label, children }: DetailRowProps) {
  return (
    <div className="flex items-start gap-3">
      <div className="mt-0.5 text-white/40">{icon}</div>
      <div>
        <p className="text-[11px] font-medium uppercase tracking-[0.08em] text-white/45">
          {label}
        </p>
        <p className="text-[15px] text-white/85">{children}</p>
      </div>
    </div>
  );
}
