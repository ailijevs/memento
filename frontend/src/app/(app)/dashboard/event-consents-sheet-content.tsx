"use client";

import { Ban, Loader2, ShieldCheck } from "lucide-react";
import type { ConsentResponse } from "@/lib/api";

interface EventConsentsSheetContentProps {
  loading: boolean;
  saving: boolean;
  consent: ConsentResponse | null;
  onToggleProfileDisplay: (next: boolean) => void;
  onToggleRecognition: (next: boolean) => void;
  onGrantAll: () => void;
  onRevokeAll: () => void;
}

export function EventConsentsSheetContent({
  loading,
  saving,
  consent,
  onToggleProfileDisplay,
  onToggleRecognition,
  onGrantAll,
  onRevokeAll,
}: EventConsentsSheetContentProps) {
  if (loading) {
    return (
      <div className="flex items-center justify-center py-10">
        <Loader2 className="h-5 w-5 animate-spin text-white/45" />
      </div>
    );
  }

  if (!consent) {
    return (
      <div
        className="rounded-2xl px-4 py-4 text-[13px] text-white/70"
        style={{
          background: "oklch(1 0 0 / 4%)",
          border: "1px solid oklch(1 0 0 / 10%)",
        }}
      >
        Could not load your event consent settings.
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div
        className="rounded-2xl p-3 text-[12px] text-white/70"
        style={{
          background: "oklch(1 0 0 / 4%)",
          border: "1px solid oklch(1 0 0 / 10%)",
        }}
      >
        Update how this event can use your profile and face recognition data.
      </div>

      <ConsentRow
        title="Profile Display"
        description="When off, other attendees cannot view your RSVP profile card, your RSVP list visibility is limited, and this also affects post-recognition profile cards for both who you can see and who can see your profile."
        enabled={consent.allow_profile_display}
        disabled={saving}
        onToggle={onToggleProfileDisplay}
      />

      <ConsentRow
        title="Face Recognition"
        description="When on, your profile photo can be added to this event recognition collection. Turning it off removes your face data from this event collection."
        enabled={consent.allow_recognition}
        disabled={saving}
        onToggle={onToggleRecognition}
      />

      <div className="grid grid-cols-2 gap-2 pt-1">
        <button
          onClick={onGrantAll}
          disabled={saving || (consent.allow_profile_display && consent.allow_recognition)}
          className="inline-flex items-center justify-center gap-2 rounded-xl px-3 py-2 text-[11px] font-medium uppercase tracking-[0.09em] text-white/85 transition-transform active:scale-95 disabled:opacity-50"
          style={{
            background: "oklch(0.23 0.11 145 / 60%)",
            border: "1px solid oklch(0.58 0.14 145 / 34%)",
          }}
        >
          {saving ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <ShieldCheck className="h-3.5 w-3.5" />}
          Grant All
        </button>
        <button
          onClick={onRevokeAll}
          disabled={saving || (!consent.allow_profile_display && !consent.allow_recognition)}
          className="inline-flex items-center justify-center gap-2 rounded-xl px-3 py-2 text-[11px] font-medium uppercase tracking-[0.09em] text-white/85 transition-transform active:scale-95 disabled:opacity-50"
          style={{
            background: "oklch(0.25 0.1 30 / 58%)",
            border: "1px solid oklch(0.59 0.16 30 / 34%)",
          }}
        >
          {saving ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Ban className="h-3.5 w-3.5" />}
          Revoke All
        </button>
      </div>
    </div>
  );
}

interface ConsentRowProps {
  title: string;
  description: string;
  enabled: boolean;
  disabled: boolean;
  onToggle: (next: boolean) => void;
}

function ConsentRow({ title, description, enabled, disabled, onToggle }: ConsentRowProps) {
  return (
    <div
      className="rounded-2xl p-3"
      style={{
        background: "oklch(1 0 0 / 4%)",
        border: "1px solid oklch(1 0 0 / 10%)",
      }}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-[14px] font-medium text-white/90">{title}</p>
          <p className="mt-1 text-[12px] text-white/55">{description}</p>
        </div>
        <button
          type="button"
          role="switch"
          aria-checked={enabled}
          aria-label={title}
          disabled={disabled}
          onClick={() => onToggle(!enabled)}
          className="relative inline-flex h-6 w-11 shrink-0 rounded-full transition-colors disabled:opacity-55"
          style={{
            background: enabled ? "oklch(0.59 0.18 160 / 90%)" : "oklch(1 0 0 / 18%)",
            border: enabled
              ? "1px solid oklch(0.72 0.14 160 / 58%)"
              : "1px solid oklch(1 0 0 / 20%)",
          }}
        >
          <span
            className="absolute top-[1px] h-[20px] w-[20px] rounded-full bg-white transition-transform"
            style={{
              transform: enabled ? "translateX(21px)" : "translateX(1px)",
            }}
          />
        </button>
      </div>
    </div>
  );
}
