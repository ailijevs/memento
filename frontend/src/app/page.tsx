"use client";

import { useState, useCallback, useRef } from "react";
import { Aurora } from "@/components/aurora";
import { SignupContent } from "@/components/signup-content";
import { LoginContent } from "@/components/login-content";

type Screen = "welcome" | "signup" | "login";

export default function App() {
  const [screen, setScreen] = useState<Screen>("welcome");
  const [contentVisible, setContentVisible] = useState(true);

  // Galaxy zoom state
  const [zoomOrigin, setZoomOrigin] = useState<{ x: number; y: number } | null>(null);
  const [zoomIn, setZoomIn] = useState(false);
  const [blurClearing, setBlurClearing] = useState(false);
  const navigatingRef = useRef(false);

  const userPosRef = useRef({ x: 50, y: 35 });
  const handleUserPosition = useCallback((xPct: number, yPct: number) => {
    userPosRef.current = { x: xPct * 100, y: yPct * 100 };
  }, []);

  const navigateTo = useCallback((dest: Screen) => {
    if (navigatingRef.current) return;
    navigatingRef.current = true;

    const { x, y } = userPosRef.current;

    setContentVisible(false);
    setZoomOrigin({ x, y });
    setZoomIn(false);
    setBlurClearing(false);

    // Double rAF: let origin paint before zoom starts so transition fires correctly
    requestAnimationFrame(() =>
      requestAnimationFrame(() => setZoomIn(true))
    );

    // At peak zoom (~500ms): swap content, snap scale back (hidden by blur), begin clearing
    setTimeout(() => {
      setScreen(dest);
      window.history.pushState(null, "", `/${dest}`);
      setZoomIn(false);       // scale snaps to 1 instantly — invisible under blur
      setBlurClearing(true);  // blur fades to 0 over 450ms → auth materializes
      setContentVisible(true);
    }, 500);

    // Cleanup
    setTimeout(() => {
      setZoomOrigin(null);
      setBlurClearing(false);
      navigatingRef.current = false;
    }, 960);
  }, []);

  const navigateBack = useCallback(() => {
    if (navigatingRef.current) return;
    navigatingRef.current = true;
    setContentVisible(false);
    setTimeout(() => {
      setScreen("welcome");
      window.history.pushState(null, "", "/");
      setContentVisible(true);
      navigatingRef.current = false;
    }, 220);
  }, []);

  const isAuth = screen !== "welcome";

  // Build zoom style: zoom in → blur up → snap scale to 1 → blur down → done
  const zoomWrapStyle: React.CSSProperties = zoomOrigin
    ? {
        transform: zoomIn ? "scale(8)" : "scale(1)",
        transformOrigin: `${zoomOrigin.x}% ${zoomOrigin.y}%`,
        filter: zoomIn
          ? "blur(20px) brightness(2)"
          : blurClearing
            ? "blur(0px) brightness(1)"
            : "none",
        transition: zoomIn
          ? "transform 0.5s cubic-bezier(0.4, 0, 1, 1), filter 0.5s ease"
          : blurClearing
            ? "filter 0.45s ease"
            : "none",
        willChange: "transform, filter",
      }
    : {};

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
      {/* Galaxy zoom wrapper — entire scene zooms into the "You" particle */}
      <div className="absolute inset-0 flex flex-col" style={zoomWrapStyle}>
        {/* Aurora — fades to 18% on auth screens */}
        <div
          className="absolute inset-0"
          style={{ opacity: isAuth ? 0.18 : 1, transition: "opacity 0.6s ease" }}
        >
          <Aurora mode="full" onUserPosition={handleUserPosition} />
        </div>

        {/* Screen content */}
        <div
          className="relative z-10 flex flex-1 flex-col"
          style={{
            opacity: contentVisible ? 1 : 0,
            transition: "opacity 0.22s ease",
            pointerEvents: contentVisible ? "auto" : "none",
          }}
        >
          {screen === "welcome" && <WelcomeScreen onNavigate={navigateTo} />}
          {screen === "signup" && (
            <SignupContent onBack={navigateBack} showYouDot />
          )}
          {screen === "login" && (
            <LoginContent
              onBack={navigateBack}
              onGoSignup={() => navigateTo("signup")}
              showYouDot
            />
          )}
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────
// Welcome screen content
// ─────────────────────────────────────────
function WelcomeScreen({ onNavigate }: { onNavigate: (dest: Screen) => void }) {
  return (
    <>
      <div className="flex-1" />
      <div className="relative px-6 pb-12">
        <div
          className="pointer-events-none absolute -left-10 -top-16 h-[160px] w-[360px]"
          style={{
            background:
              "radial-gradient(ellipse at 40% 55%, oklch(0.06 0.02 270 / 90%) 0%, transparent 70%)",
            filter: "blur(50px)",
          }}
          aria-hidden
        />

        <div
          className="animate-fade-in mb-5 h-px w-16"
          style={{
            background:
              "linear-gradient(90deg, oklch(0.5 0.15 275 / 60%), transparent)",
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
            onClick={() => onNavigate("signup")}
            className="animate-fade-up delay-400 flex h-[56px] w-full items-center justify-center rounded-[16px] text-body font-semibold tracking-[-0.01em] text-white/90 transition-all active:scale-[0.98] active:bg-white/[0.08]"
            style={{
              background: "oklch(1 0 0 / 5%)",
              boxShadow:
                "inset 0 0 0 1px oklch(0.5 0.15 275 / 20%), 0 0 30px oklch(0.4 0.12 275 / 12%)",
            }}
          >
            Get Started
          </button>
          <button
            onClick={() => onNavigate("login")}
            className="animate-fade-in delay-500 mt-3 flex h-[50px] w-full items-center justify-center rounded-[16px] text-subhead text-white/30 transition-colors active:text-white/60"
          >
            I already have an account
          </button>
        </div>
      </div>
    </>
  );
}
