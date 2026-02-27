"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ChevronLeft } from "lucide-react";
import { Aurora } from "@/components/aurora";

export default function LocationPage() {
  const router = useRouter();
  const [location, setLocation] = useState("");

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
          Step 5 of 8
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
          Where are you based?
        </h1>
        <p className="mt-2 text-[14px] leading-relaxed text-white/38">
          Helps people find connections nearby.
        </p>
      </div>

      {/* Input card */}
      <div
        className="relative z-10 flex-1 px-6"
        style={{ animation: "fade-in 0.5s cubic-bezier(0.16,1,0.3,1) 100ms both" }}
      >
        <div
          className="overflow-hidden rounded-2xl"
          style={{
            background: "rgba(255,255,255,0.04)",
            border: "1px solid rgba(255,255,255,0.08)",
          }}
        >
          <input
            type="text"
            placeholder="San Francisco, CA"
            autoComplete="off"
            autoFocus
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && location.trim()) router.push("/onboarding/bio"); }}
            className="w-full bg-transparent px-5 py-5 text-[20px] text-white outline-none placeholder:text-white/15"
            style={{ caretColor: "oklch(0.7 0.18 275)" }}
          />
        </div>
      </div>

      {/* Bottom actions */}
      <div
        className="relative z-10 px-6 pb-4 pt-8"
        style={{ animation: "fade-in 0.5s cubic-bezier(0.16,1,0.3,1) 200ms both" }}
      >
        <button
          type="button"
          onClick={() => router.push("/onboarding/bio")}
          disabled={!location.trim()}
          className="flex h-[56px] w-full items-center justify-center rounded-[16px] text-[15px] font-semibold tracking-[-0.01em] text-white/90 transition-all active:scale-[0.98] disabled:opacity-30"
          style={{
            background: "oklch(1 0 0 / 6%)",
            boxShadow: "inset 0 0 0 1px oklch(0.5 0.15 275 / 25%), 0 0 30px oklch(0.4 0.12 275 / 15%)",
          }}
        >
          Continue
        </button>

        <button
          type="button"
          onClick={() => router.push("/onboarding/bio")}
          className="mt-4 flex w-full items-center justify-center text-[13px] text-white/30 active:text-white/50"
        >
          Skip for now
        </button>
      </div>

      <div className="relative z-10 h-4" />
    </div>
  );
}
