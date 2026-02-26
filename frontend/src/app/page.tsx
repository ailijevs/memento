"use client";

import { useState, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Aurora } from "@/components/aurora";

export default function WelcomePage() {
  const router = useRouter();
  const [zooming, setZooming] = useState(false);
  const userPosRef = useRef({ x: 50, y: 35 });
  const [zoomOrigin, setZoomOrigin] = useState("50% 35%");

  const handleUserPosition = useCallback((xPct: number, yPct: number) => {
    userPosRef.current = { x: xPct * 100, y: yPct * 100 };
  }, []);

  const handleGetStarted = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();
      const { x, y } = userPosRef.current;
      setZoomOrigin(`${x.toFixed(1)}% ${y.toFixed(1)}%`);
      setZooming(true);
      setTimeout(() => router.push("/signup"), 750);
    },
    [router],
  );

  return (
    <div
      className="relative flex min-h-dvh flex-col overflow-hidden"
      style={{
        background: [
          "radial-gradient(ellipse 90% 50% at 50% 38%, oklch(0.11 0.06 275) 0%, transparent 100%)",
          "radial-gradient(ellipse 50% 35% at 68% 52%, oklch(0.08 0.04 240) 0%, transparent 100%)",
          "radial-gradient(ellipse 40% 30% at 30% 60%, oklch(0.06 0.03 260) 0%, transparent 100%)",
          "oklch(0.04 0.005 270)",
        ].join(", "),
      }}
    >
      {/* Aurora — zooms toward the white dot */}
      <div
        className="absolute inset-0"
        style={{
          transformOrigin: zoomOrigin,
          transform: zooming ? "scale(2.4)" : "scale(1)",
          transition: zooming ? "transform 0.7s cubic-bezier(0.22, 1, 0.36, 1)" : undefined,
        }}
      >
        <Aurora className="h-full w-full" onUserPosition={handleUserPosition} />
      </div>

      {/* Content fades out during zoom */}
      <div
        className="relative z-10 flex flex-1 flex-col"
        style={{
          opacity: zooming ? 0 : 1,
          transition: "opacity 0.3s ease-out",
        }}
      >
        <div className="flex-1" />

        <div className="relative px-6 pb-12">
          <div
            className="pointer-events-none absolute -left-10 -top-16 h-[160px] w-[360px]"
            style={{
              background: "radial-gradient(ellipse at 40% 55%, oklch(0.06 0.02 270 / 90%) 0%, transparent 70%)",
              filter: "blur(50px)",
            }}
            aria-hidden
          />

          <div
            className="animate-fade-in mb-5 h-px w-16"
            style={{
              background: "linear-gradient(90deg, oklch(0.5 0.15 275 / 60%), transparent)",
            }}
          />

          <h1
            className="animate-focus-in relative"
            style={{
              fontFamily: "var(--font-serif)",
              fontSize: 48,
              fontWeight: 400,
              letterSpacing: "-0.02em",
              lineHeight: 1,
              color: "white",
            }}
          >
            Memento
          </h1>

          <p className="animate-fade-up delay-200 relative mt-3 text-callout tracking-[-0.01em] text-white/70">
            Know who you&apos;re talking to.
          </p>
          <p className="animate-fade-up delay-300 relative mt-1 text-subhead tracking-[-0.01em] text-white/45">
            Before a word is spoken.
          </p>

          <div className="mt-8">
            <button
              onClick={handleGetStarted}
              className="animate-fade-up delay-400 flex h-[56px] w-full items-center justify-center rounded-[16px] text-body font-semibold tracking-[-0.01em] text-white/90 transition-all active:scale-[0.98] active:bg-white/[0.08]"
              style={{
                background: "oklch(1 0 0 / 5%)",
                boxShadow: "inset 0 0 0 1px oklch(0.5 0.15 275 / 20%), 0 0 30px oklch(0.4 0.12 275 / 12%)",
              }}
            >
              Get Started
            </button>
            <Link
              href="/login"
              className="animate-fade-in delay-500 mt-3 flex h-[50px] w-full items-center justify-center rounded-[16px] text-subhead text-white/30 transition-colors active:text-white/60"
            >
              I already have an account
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
