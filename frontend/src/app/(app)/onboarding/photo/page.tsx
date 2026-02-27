"use client";

import { useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { ChevronLeft, Camera } from "lucide-react";
import { Aurora } from "@/components/aurora";

export default function PhotoPage() {
  const router = useRouter();
  const [preview, setPreview] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    const url = URL.createObjectURL(file);
    setPreview(url);
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
          Step 4 of 8
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
          Add a photo
        </h1>
        <p className="mt-2 text-[14px] leading-relaxed text-white/38">
          A clear face photo helps others recognize you.
        </p>
      </div>

      {/* Avatar + picker */}
      <div
        className="relative z-10 flex flex-1 flex-col items-center justify-start pt-4"
        style={{ animation: "fade-in 0.5s cubic-bezier(0.16,1,0.3,1) 100ms both" }}
      >
        {/* Circle */}
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          className="relative flex h-[96px] w-[96px] items-center justify-center rounded-full transition-all active:scale-95"
          style={{
            border: "1.5px solid rgba(255,255,255,0.12)",
            background: preview ? "transparent" : "rgba(255,255,255,0.03)",
          }}
        >
          {preview ? (
            <img
              src={preview}
              alt="Profile preview"
              className="h-full w-full rounded-full object-cover"
            />
          ) : (
            <Camera className="h-8 w-8 text-white/20" />
          )}
        </button>

        {/* Choose photo button */}
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          className="mt-5 rounded-full px-5 py-2 text-[13px] font-medium text-white/50 transition-all active:text-white/80"
          style={{
            background: "rgba(255,255,255,0.04)",
            border: "1px solid rgba(255,255,255,0.08)",
          }}
        >
          {preview ? "Change photo" : "Choose photo"}
        </button>

        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          className="hidden"
          onChange={handleFileChange}
        />
      </div>

      {/* Bottom actions */}
      <div
        className="relative z-10 px-6 pb-4"
        style={{ animation: "fade-in 0.5s cubic-bezier(0.16,1,0.3,1) 200ms both" }}
      >
        <button
          type="button"
          onClick={() => router.push("/onboarding/location")}
          className="flex h-[56px] w-full items-center justify-center rounded-[16px] text-[15px] font-semibold tracking-[-0.01em] text-white/90 transition-all active:scale-[0.98]"
          style={{
            background: "oklch(1 0 0 / 6%)",
            boxShadow: "inset 0 0 0 1px oklch(0.5 0.15 275 / 25%), 0 0 30px oklch(0.4 0.12 275 / 15%)",
          }}
        >
          Continue
        </button>

        <button
          type="button"
          onClick={() => router.push("/onboarding/location")}
          className="mt-4 flex w-full items-center justify-center text-[13px] text-white/30 active:text-white/50"
        >
          Skip for now
        </button>
      </div>

      <div className="relative z-10 h-4" />
    </div>
  );
}
