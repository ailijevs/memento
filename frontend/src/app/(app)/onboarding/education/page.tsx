"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ChevronLeft, Plus, Loader2 } from "lucide-react";
import { Aurora } from "@/components/aurora";
import { createClient } from "@/lib/supabase/client";
import { api } from "@/lib/api";
import { getNextRoute } from "@/lib/onboarding";

interface EducationEntry {
  school: string;
  degree: string;
}

const MAX_ENTRIES = 3;

export default function EducationPage() {
  const router = useRouter();
  const [entries, setEntries] = useState<EducationEntry[]>([{ school: "", degree: "" }]);

  function updateEntry(index: number, field: keyof EducationEntry, value: string) {
    setEntries((prev) => prev.map((e, i) => (i === index ? { ...e, [field]: value } : e)));
  }

  function addEntry() {
    if (entries.length < MAX_ENTRIES) {
      setEntries((prev) => [...prev, { school: "", degree: "" }]);
    }
  }

  const hasAny = entries.some((e) => e.school.trim() || e.degree.trim());
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleContinue() {
    const filled = entries.filter((e) => e.school.trim() || e.degree.trim());
    if (!filled.length) return;
    setLoading(true);
    setError(null);
    try {
      const supabase = createClient();
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) { setError("Session expired. Please sign in again."); return; }
      api.setToken(session.access_token);
      await api.updateProfile({
        education: filled.map((e) => ({ school: e.school.trim() || null, degree: e.degree.trim() || null })),
      });
      router.push(getNextRoute("education"));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="relative flex min-h-dvh flex-col overflow-hidden">
      {/* Aurora — full mode dimmed, matches welcome page glow */}
      <div className="absolute inset-0" style={{ opacity: 0.28 }}>
        <Aurora className="h-full w-full" mode="ambient" />
      </div>

      {/* Edge fades */}
      <div
        className="pointer-events-none absolute inset-0"
        style={{
          background: [
            "linear-gradient(to top, oklch(0.04 0.005 270) 15%, transparent 42%)",
            "linear-gradient(to bottom, oklch(0.04 0.005 270 / 50%) 0%, transparent 22%)",
          ].join(", "),
        }}
      />

      {/* Back button */}
      <div className="relative z-10 px-6 pt-4">
        <button
          onClick={() => router.back()}
          className="inline-flex h-[44px] items-center text-white/30 active:text-white/60"
        >
          <ChevronLeft className="h-5 w-5" />
        </button>
      </div>

      {/* Header */}
      <div
        className="relative z-10 px-6 pb-8"
        style={{ animation: "fade-in 0.5s cubic-bezier(0.16,1,0.3,1) both" }}
      >
        <p className="mb-2 text-[10px] font-semibold uppercase tracking-[0.18em] text-white/22">
          Step 8 of 8
        </p>
        <h1
          className="text-white"
          style={{
            fontFamily: "var(--font-serif)",
            fontSize: 32,
            fontWeight: 400,
            letterSpacing: "-0.02em",
            lineHeight: 1.1,
          }}
        >
          Where did you study?
        </h1>
        <p className="mt-2 text-[14px] leading-relaxed text-white/38">
          Your educational background helps people connect with you.
        </p>
      </div>

      {/* Entry cards */}
      <div
        className="relative z-10 flex-1 space-y-3 px-6"
        style={{ animation: "fade-in 0.5s cubic-bezier(0.16,1,0.3,1) 100ms both" }}
      >
        {entries.map((entry, i) => (
          <div
            key={i}
            className="overflow-hidden rounded-2xl"
            style={{
              background: "rgba(255,255,255,0.04)",
              border: "1px solid rgba(255,255,255,0.08)",
            }}
          >
            <input
              type="text"
              placeholder="School"
              autoFocus={i === 0}
              value={entry.school}
              onChange={(e) => updateEntry(i, "school", e.target.value)}
              className="w-full bg-transparent px-5 py-4 text-[16px] text-white outline-none placeholder:text-white/15"
              style={{ caretColor: "oklch(0.7 0.18 275)" }}
            />
            <div style={{ height: "1px", background: "rgba(255,255,255,0.06)", margin: "0 20px" }} />
            <input
              type="text"
              placeholder="Degree + field of study"
              value={entry.degree}
              onChange={(e) => updateEntry(i, "degree", e.target.value)}
              className="w-full bg-transparent px-5 py-4 text-[16px] text-white outline-none placeholder:text-white/15"
              style={{ caretColor: "oklch(0.7 0.18 275)" }}
            />
          </div>
        ))}

        {entries.length < MAX_ENTRIES && (
          <button
            type="button"
            onClick={addEntry}
            className="flex items-center gap-1.5 text-[13px] text-white/30 active:text-white/50"
          >
            <Plus className="h-3.5 w-3.5" />
            Add another
          </button>
        )}
      </div>

      {/* Bottom actions */}
      <div
        className="relative z-10 px-6 pb-4 pt-8"
        style={{ animation: "fade-in 0.5s cubic-bezier(0.16,1,0.3,1) 200ms both" }}
      >
        <button
          type="button"
          onClick={handleContinue}
          disabled={!hasAny || loading}
          className="flex h-[56px] w-full items-center justify-center gap-2 rounded-[16px] text-[15px] font-semibold tracking-[-0.01em] text-white/90 transition-all active:scale-[0.98] disabled:opacity-30"
          style={{
            background: "oklch(1 0 0 / 6%)",
            boxShadow: "inset 0 0 0 1px oklch(0.5 0.15 275 / 25%), 0 0 30px oklch(0.4 0.12 275 / 15%)",
          }}
        >
          {loading ? <Loader2 className="h-4 w-4 animate-spin text-white/60" /> : "Finish"}
        </button>
        {error && <p className="mt-2 text-center text-[13px] text-red-400/80">{error}</p>}

        <button
          type="button"
          onClick={() => router.push(getNextRoute("education"))}
          className="mt-4 flex w-full items-center justify-center text-[13px] text-white/30 active:text-white/50"
        >
          Skip for now
        </button>
      </div>

      <div className="relative z-10 h-4" />
    </div>
  );
}
