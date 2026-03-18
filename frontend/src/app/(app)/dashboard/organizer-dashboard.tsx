"use client";

import { Plus } from "lucide-react";

interface OrganizerControlsProps {
  onCreateEvent: () => void;
}

export function OrganizerControls({ onCreateEvent }: OrganizerControlsProps) {
  return (
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
  );
}

export function OrganizerContent() {
  return (
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
  );
}
