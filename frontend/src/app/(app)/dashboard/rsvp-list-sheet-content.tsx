"use client";

import { useState } from "react";
import { Loader2, GraduationCap, BriefcaseBusiness, UserRound } from "lucide-react";
import type { ProfileDirectoryEntry } from "@/lib/api";

interface RsvpListSheetContentProps {
  loading: boolean;
  entries: ProfileDirectoryEntry[];
  totalCount: number;
  hiddenCount: number;
  showConsentOffNotice?: boolean;
}

function resolvePhotoUrl(photoPath: string | null): string | null {
  if (!photoPath) return null;
  const normalized = photoPath.trim();
  if (!normalized) return null;
  return normalized;
}

export function RsvpListSheetContent({
  loading,
  entries,
  totalCount,
  hiddenCount,
  showConsentOffNotice = false,
}: RsvpListSheetContentProps) {
  return (
    <div className="min-h-0 flex-1 flex flex-col">
      {showConsentOffNotice ? (
        <div
          className="mb-3 rounded-2xl px-3 py-2 text-[12px] text-amber-200/90"
          style={{
            background: "oklch(0.3 0.09 70 / 22%)",
            border: "1px solid oklch(0.72 0.14 70 / 38%)",
          }}
        >
          Your profile display consent is off. You won&apos;t be able to view other attendees&apos;
          profiles.
        </div>
      ) : null}
      <div
        className="mb-3 rounded-2xl px-3 py-2 text-[12px] text-white/75"
        style={{
          background: "oklch(1 0 0 / 4%)",
          border: "1px solid oklch(1 0 0 / 10%)",
        }}
      >
        <span className="font-medium text-white/90">{totalCount}</span> RSVP&apos;d
        {hiddenCount > 0 ? (
          <>
            {" · "}
            <span className="font-medium text-white/90">{hiddenCount}</span> hidden
          </>
        ) : null}
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto space-y-3 pr-1 pb-2">
        {loading ? (
          <div className="flex items-center justify-center py-10">
            <Loader2 className="h-5 w-5 animate-spin text-white/45" />
          </div>
        ) : entries.length === 0 ? (
          <>
            <div
              className="rounded-3xl px-5 py-8 text-center"
              style={{
                background: "oklch(1 0 0 / 4%)",
                border: "1px solid oklch(1 0 0 / 8%)",
              }}
            >
              <p className="text-[16px] text-white/75">No RSVPs yet</p>
            </div>
            {hiddenCount > 0 ? (
              <HiddenAttendeesCard hiddenCount={hiddenCount} />
            ) : null}
          </>
        ) : (
          <>
            {entries.map((entry, index) => (
              <RsvpProfileCard key={entry.user_id} entry={entry} index={index} />
            ))}
            {hiddenCount > 0 ? (
              <HiddenAttendeesCard hiddenCount={hiddenCount} />
            ) : null}
          </>
        )}
      </div>
    </div>
  );
}

function RsvpProfileCard({ entry, index }: { entry: ProfileDirectoryEntry; index: number }) {
  const [imgFailed, setImgFailed] = useState(false);
  const name = entry.full_name || "Unknown person";
  const initials = name
    .split(" ")
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
  const photoUrl = resolvePhotoUrl(entry.photo_path);

  return (
    <div
      className="rounded-2xl p-4 transition-transform"
      style={{
        background: "rgba(255,255,255,0.07)",
        border: "1px solid rgba(255,255,255,0.12)",
        animation: `fade-in 0.4s cubic-bezier(0.16,1,0.3,1) ${index * 40}ms both`,
      }}
    >
      <div className="flex items-start gap-3">
        {photoUrl && !imgFailed ? (
          <img
            src={photoUrl}
            alt={name}
            className="h-12 w-12 shrink-0 rounded-full object-cover mt-0.5"
            style={{ border: "1px solid rgba(255,255,255,0.10)" }}
            onError={() => setImgFailed(true)}
          />
        ) : (
          <div
            className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full text-[15px] font-medium text-white/60 mt-0.5"
            style={{
              background: "rgba(255,255,255,0.06)",
              border: "1px solid rgba(255,255,255,0.10)",
            }}
          >
            {initials}
          </div>
        )}

        <div className="min-w-0 flex-1">
          <p className="truncate text-[15px] font-semibold text-white">{name}</p>
          {entry.headline ? (
            <p className="truncate text-[13px] text-white/55 mt-0.5">{entry.headline}</p>
          ) : null}

          <div className="mt-2 flex flex-wrap gap-2">
            {entry.company ? (
              <span
                className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium"
                style={{
                  background: "oklch(0.33 0.1 210 / 40%)",
                  border: "1px solid oklch(0.55 0.15 210 / 28%)",
                  color: "oklch(0.86 0.05 230)",
                }}
              >
                <BriefcaseBusiness className="h-3 w-3" />
                {entry.company}
              </span>
            ) : null}
            {entry.school ? (
              <span
                className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium"
                style={{
                  background: "oklch(0.35 0.08 275 / 40%)",
                  border: "1px solid oklch(0.5 0.15 275 / 25%)",
                  color: "oklch(0.8 0.1 275)",
                }}
              >
                <GraduationCap className="h-3 w-3" />
                {entry.school}
              </span>
            ) : null}
            {entry.major ? (
              <span
                className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium"
                style={{
                  background: "oklch(0.31 0.09 140 / 40%)",
                  border: "1px solid oklch(0.52 0.13 140 / 25%)",
                  color: "oklch(0.82 0.08 150)",
                }}
              >
                <UserRound className="h-3 w-3" />
                {entry.major}
              </span>
            ) : null}
          </div>
        </div>
      </div>
    </div>
  );
}

function HiddenAttendeesCard({ hiddenCount }: { hiddenCount: number }) {
  const previewCount = Math.min(hiddenCount, 4);
  return (
    <div
      className="rounded-2xl p-4"
      style={{
        background: "oklch(1 0 0 / 5%)",
        border: "1px dashed oklch(1 0 0 / 16%)",
      }}
    >
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-[14px] font-semibold text-white/90">+{hiddenCount} more</p>
          <p className="mt-0.5 text-[12px] text-white/45">Hidden by attendee privacy settings</p>
        </div>
        <div className="flex items-center">
          {Array.from({ length: previewCount }).map((_, idx) => (
            <div
              key={idx}
              className="flex h-8 w-8 items-center justify-center rounded-full text-white/60"
              style={{
                marginLeft: idx === 0 ? 0 : -10,
                background: "rgba(255,255,255,0.08)",
                border: "1px solid rgba(255,255,255,0.18)",
              }}
            >
              <UserRound className="h-4 w-4" />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
