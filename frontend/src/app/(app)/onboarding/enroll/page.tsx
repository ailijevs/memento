"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ScanFace, Loader2, CheckCircle } from "lucide-react";
import { Aurora } from "@/components/aurora";
import { createClient } from "@/lib/supabase/client";
import { api } from "@/lib/api";

const EVENT_ID = process.env.NEXT_PUBLIC_RECOGNITION_EVENT_ID ?? "";

export default function EnrollPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [enrolled, setEnrolled] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleEnroll() {
    if (!EVENT_ID) {
      setError("No event configured. You can skip this step.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const supabase = createClient();
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) { router.push("/"); return; }
      api.setToken(session.access_token);
      await api.enrollFace(EVENT_ID);
      setEnrolled(true);
      setTimeout(() => router.push("/dashboard"), 1200);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Enrollment failed. You can skip this step.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="relative flex min-h-dvh flex-col overflow-hidden">
      <div className="absolute inset-0" style={{ opacity: 0.52 }}>
        <Aurora className="h-full w-full" mode="ambient" />
      </div>

      <div
        className="pointer-events-none absolute inset-0"
        style={{
          background: [
            "linear-gradient(to top, oklch(0.07 0.015 270) 15%, transparent 42%)",
            "linear-gradient(to bottom, oklch(0.04 0.005 270 / 50%) 0%, transparent 22%)",
          ].join(", "),
        }}
      />

      {/* Header */}
      <div
        className="relative z-10 px-6 pt-16 pb-8"
        style={{ animation: "fade-in 0.5s cubic-bezier(0.16,1,0.3,1) both" }}
      >
        <p className="mb-2 text-[10px] font-semibold uppercase tracking-[0.18em] text-white/22">
          Almost done
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
          Enable face recognition
        </h1>
        <p className="mt-2 text-[14px] leading-relaxed text-white/38">
          Let Memento recognize you at this event so others can connect with you.
        </p>
      </div>

      {/* Icon */}
      <div
        className="relative z-10 flex flex-1 flex-col items-center justify-start pt-8"
        style={{ animation: "fade-in 0.5s cubic-bezier(0.16,1,0.3,1) 100ms both" }}
      >
        <div
          className="flex h-24 w-24 items-center justify-center rounded-full"
          style={{
            background: enrolled
              ? "oklch(0.25 0.1 145 / 40%)"
              : "rgba(255,255,255,0.04)",
            border: enrolled
              ? "1.5px solid oklch(0.5 0.15 145 / 40%)"
              : "1.5px solid rgba(255,255,255,0.10)",
            transition: "all 0.4s ease",
          }}
        >
          {enrolled ? (
            <CheckCircle className="h-10 w-10" style={{ color: "oklch(0.75 0.15 145)" }} />
          ) : (
            <ScanFace className="h-10 w-10 text-white/25" />
          )}
        </div>
        {enrolled && (
          <p
            className="mt-4 text-[14px] font-medium"
            style={{ color: "oklch(0.75 0.15 145)", animation: "fade-in 0.4s ease both" }}
          >
            You&apos;re enrolled!
          </p>
        )}
      </div>

      {/* Bottom actions */}
      <div
        className="relative z-10 px-6 pb-4"
        style={{ animation: "fade-in 0.5s cubic-bezier(0.16,1,0.3,1) 200ms both" }}
      >
        {error && <p className="mb-3 text-center text-[13px] text-red-400/80">{error}</p>}

        <button
          type="button"
          onClick={handleEnroll}
          disabled={loading || enrolled}
          className="flex h-[56px] w-full items-center justify-center gap-2 rounded-[16px] text-[15px] font-semibold tracking-[-0.01em] text-white/90 transition-all active:scale-[0.98] disabled:opacity-60"
          style={{
            background: "oklch(1 0 0 / 6%)",
            boxShadow: "inset 0 0 0 1px oklch(0.5 0.15 275 / 25%), 0 0 30px oklch(0.4 0.12 275 / 15%)",
          }}
        >
          {loading ? (
            <Loader2 className="h-4 w-4 animate-spin text-white/60" />
          ) : enrolled ? (
            "Enrolled"
          ) : (
            "Enroll my face"
          )}
        </button>

        <button
          type="button"
          onClick={() => router.push("/dashboard")}
          className="mt-4 flex w-full items-center justify-center text-[13px] text-white/30 active:text-white/50"
        >
          Skip for now
        </button>
      </div>

      <div className="relative z-10 h-4" />
    </div>
  );
}
