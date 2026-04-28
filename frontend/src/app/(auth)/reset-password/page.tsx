"use client";

import { useState, useRef, useEffect, useCallback, Suspense } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { Loader2, ChevronLeft, ChevronRight, CheckCircle, AlertCircle } from "lucide-react";
import { Aurora } from "@/components/aurora";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const FIELDS = [
  {
    key: "password",
    label: "New Password",
    type: "password" as const,
    placeholder: "At least 6 characters",
    autoComplete: "new-password",
    color: [100, 75, 240] as const,
    glow: "rgba(100,75,240,0.45)",
    pos: { left: 30, top: 40 },
    float: "float-2 15s ease-in-out infinite",
  },
  {
    key: "confirm_password",
    label: "Confirm Password",
    type: "password" as const,
    placeholder: "Repeat password",
    autoComplete: "new-password",
    color: [70, 110, 230] as const,
    glow: "rgba(70,110,230,0.45)",
    pos: { left: 65, top: 52 },
    float: "float-3 14s ease-in-out infinite",
  },
];

function displayValue(val: string, type: string) {
  if (!val) return "";
  if (type === "password") return "••••••";
  if (val.length > 16) return val.slice(0, 15) + "…";
  return val;
}

export default function ResetPasswordPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-dvh items-center justify-center" style={{ background: "oklch(0.07 0.015 270)" }}>
          <Loader2 className="h-6 w-6 animate-spin text-white/30" />
        </div>
      }
    >
      <ResetPasswordContent />
    </Suspense>
  );
}

function ResetPasswordContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [values, setValues] = useState(["", ""]);
  const [activeIdx, setActiveIdx] = useState<number>(0);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [tokenError, setTokenError] = useState(false);

  const canvasRef = useRef<HTMLCanvasElement>(null);
  const dotRef = useRef<HTMLDivElement>(null);
  const nodeRefs = useRef<(HTMLDivElement | null)[]>([null, null]);
  const inputRef = useRef<HTMLInputElement>(null);

  const valuesRef = useRef(values);
  valuesRef.current = values;
  const activeIdxRef = useRef(activeIdx);
  activeIdxRef.current = activeIdx;

  const allFilled = values.every((v) => v.length > 0);
  const isLastField = activeIdx === FIELDS.length - 1;

  useEffect(() => {
    async function extractToken() {
      if (typeof window === "undefined") return;

      const hash = window.location.hash;
      if (hash && hash.includes("access_token")) {
        const params = new URLSearchParams(hash.substring(1));
        const accessToken = params.get("access_token");
        const refreshToken = params.get("refresh_token");

        if (accessToken && refreshToken) {
          const supabase = createClient();
          const { error } = await supabase.auth.setSession({
            access_token: accessToken,
            refresh_token: refreshToken,
          });
          if (error) {
            setTokenError(true);
          }
          return;
        }
      }

      const supabase = createClient();
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) {
        setTokenError(true);
      }
    }

    extractToken();
  }, [searchParams]);

  useEffect(() => {
    requestAnimationFrame(() => inputRef.current?.focus());
  }, [activeIdx]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);

    function resize() {
      canvas!.width = Math.round(canvas!.clientWidth * dpr);
      canvas!.height = Math.round(canvas!.clientHeight * dpr);
      ctx!.setTransform(dpr, 0, 0, dpr, 0, 0);
    }
    resize();
    window.addEventListener("resize", resize);

    let raf = 0;
    function draw() {
      raf = requestAnimationFrame(draw);
      ctx!.clearRect(0, 0, canvas!.clientWidth, canvas!.clientHeight);

      const dot = dotRef.current;
      if (!dot) return;
      const cRect = canvas!.getBoundingClientRect();
      const dRect = dot.getBoundingClientRect();
      const cx = dRect.left + dRect.width / 2 - cRect.left;
      const cy = dRect.top + dRect.height / 2 - cRect.top;

      const currentValues = valuesRef.current;
      const currentActive = activeIdxRef.current;

      for (let i = 0; i < FIELDS.length; i++) {
        const el = nodeRefs.current[i];
        if (!el) continue;
        const dotEl = el.querySelector("[data-dot]");
        if (!dotEl) continue;
        const dr = dotEl.getBoundingClientRect();
        const nx = dr.left + dr.width / 2 - cRect.left;
        const ny = dr.top + dr.height / 2 - cRect.top;

        const [cr, cg, cb] = FIELDS[i].color;
        const isActive = currentActive === i;
        const isFilled = currentValues[i].length > 0;
        const alpha = isActive ? 0.4 : isFilled ? 0.22 : 0.07;

        const grad = ctx!.createLinearGradient(cx, cy, nx, ny);
        grad.addColorStop(0, `rgba(255,255,255,${alpha * 0.6})`);
        grad.addColorStop(0.35, `rgba(${cr},${cg},${cb},${alpha})`);
        grad.addColorStop(1, `rgba(${cr},${cg},${cb},${alpha * 0.3})`);

        ctx!.strokeStyle = grad;
        ctx!.lineWidth = isActive ? 1.8 : isFilled ? 1.2 : 0.6;
        ctx!.beginPath();
        ctx!.moveTo(cx, cy);
        ctx!.lineTo(nx, ny);
        ctx!.stroke();
      }
    }

    raf = requestAnimationFrame(draw);
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", resize);
    };
  }, []);

  const handleNodePointerDown = useCallback(
    (e: React.PointerEvent, idx: number) => {
      e.preventDefault();
      setActiveIdx(idx);
    },
    [],
  );

  const handleInputKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter") {
        e.preventDefault();
        if (activeIdx < FIELDS.length - 1) {
          setActiveIdx(activeIdx + 1);
        } else if (allFilled) {
          handleSubmit();
        }
      }
      if (e.key === "Escape") {
        inputRef.current?.blur();
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [activeIdx, allFilled],
  );

  const setValue = useCallback((idx: number, val: string) => {
    setValues((prev) => prev.map((v, i) => (i === idx ? val : v)));
  }, []);

  async function handleSubmit() {
    if (values[0] !== values[1]) {
      setError("Passwords do not match");
      return;
    }

    if (values[0].length < 6) {
      setError("Password must be at least 6 characters");
      return;
    }

    setError(null);
    setLoading(true);

    try {
      const supabase = createClient();
      const { data: { session } } = await supabase.auth.getSession();

      if (!session?.access_token) {
        setTokenError(true);
        setLoading(false);
        return;
      }

      const res = await fetch(`${API_URL}/api/v1/auth/reset-password/confirm`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          access_token: session.access_token,
          new_password: values[0],
        }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Failed to reset password");
      }

      await supabase.auth.signOut();
      setSuccess(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  if (tokenError) {
    return (
      <div
        className="relative flex min-h-dvh flex-col items-center justify-center overflow-hidden px-6"
        style={{
          background: [
            "radial-gradient(ellipse 80% 50% at 50% 20%, oklch(0.22 0.14 275) 0%, transparent 100%)",
            "oklch(0.07 0.015 270)",
          ].join(", "),
        }}
      >
        <div className="absolute inset-0" style={{ opacity: 0.35 }}>
          <Aurora className="h-full w-full" mode="focused" />
        </div>

        <div className="relative z-10 flex flex-col items-center text-center">
          <div
            className="mb-6 flex h-16 w-16 items-center justify-center rounded-full"
            style={{
              background: "rgba(255,80,80,0.12)",
              border: "1.5px solid rgba(255,80,80,0.3)",
            }}
          >
            <AlertCircle className="h-7 w-7 text-red-400/80" />
          </div>

          <h1
            className="mb-3 text-white"
            style={{
              fontFamily: "var(--font-serif)",
              fontSize: 28,
              fontWeight: 400,
              letterSpacing: "-0.02em",
            }}
          >
            Link expired
          </h1>

          <p className="mb-8 max-w-[280px] text-[14px] leading-relaxed text-white/40">
            This password reset link is invalid or has expired. Please request a new one.
          </p>

          <Link
            href="/forgot-password"
            className="flex items-center gap-2 rounded-full px-5 py-2.5 text-[13px] font-medium text-white/70 transition-all active:scale-95"
            style={{
              background: "rgba(100,75,240,0.12)",
              border: "1px solid rgba(100,75,240,0.25)",
            }}
          >
            Request new link
          </Link>

          <Link
            href="/login"
            className="mt-6 text-[13px] text-white/25 active:text-white/50"
          >
            Back to sign in
          </Link>
        </div>
      </div>
    );
  }

  if (success) {
    return (
      <div
        className="relative flex min-h-dvh flex-col items-center justify-center overflow-hidden px-6"
        style={{
          background: [
            "radial-gradient(ellipse 80% 50% at 50% 20%, oklch(0.22 0.14 275) 0%, transparent 100%)",
            "oklch(0.07 0.015 270)",
          ].join(", "),
        }}
      >
        <div className="absolute inset-0" style={{ opacity: 0.35 }}>
          <Aurora className="h-full w-full" mode="focused" />
        </div>

        <div className="relative z-10 flex flex-col items-center text-center">
          <div
            className="mb-6 flex h-16 w-16 items-center justify-center rounded-full"
            style={{
              background: "rgba(52,168,83,0.12)",
              border: "1.5px solid rgba(52,168,83,0.3)",
            }}
          >
            <CheckCircle className="h-7 w-7 text-[rgba(52,168,83,0.8)]" />
          </div>

          <h1
            className="mb-3 text-white"
            style={{
              fontFamily: "var(--font-serif)",
              fontSize: 28,
              fontWeight: 400,
              letterSpacing: "-0.02em",
            }}
          >
            Password updated
          </h1>

          <p className="mb-8 max-w-[280px] text-[14px] leading-relaxed text-white/40">
            Your password has been reset. You can now sign in with your new password.
          </p>

          <button
            onClick={() => router.push("/login")}
            className="flex h-[50px] w-full max-w-[240px] items-center justify-center gap-2 rounded-[14px] text-[14px] font-medium text-white/90 transition-all active:scale-[0.98]"
            style={{
              background: "oklch(1 0 0 / 6%)",
              boxShadow: "inset 0 0 0 1px oklch(0.5 0.15 275 / 25%), 0 0 30px oklch(0.4 0.12 275 / 15%)",
            }}
          >
            Sign in
          </button>
        </div>
      </div>
    );
  }

  const activeField = FIELDS[activeIdx];
  const [cr, cg, cb] = activeField.color;

  return (
    <div
      className="animate-page-in relative flex min-h-dvh flex-col overflow-hidden"
      style={{
        background: [
          "radial-gradient(ellipse 80% 50% at 50% 20%, oklch(0.22 0.14 275) 0%, transparent 100%)",
          "radial-gradient(ellipse 50% 35% at 65% 50%, oklch(0.14 0.09 240) 0%, transparent 100%)",
          "oklch(0.07 0.015 270)",
        ].join(", "),
      }}
    >
      <div className="absolute inset-0" style={{ opacity: 0.45 }}>
        <Aurora className="h-full w-full" mode="focused" />
      </div>

      <canvas
        ref={canvasRef}
        className="pointer-events-none absolute inset-0 z-[5]"
        style={{ width: "100%", height: "100%" }}
        aria-hidden="true"
      />

      <div className="animate-fade-in relative z-10 px-6 pt-4">
        <Link
          href="/login"
          className="inline-flex h-[44px] items-center text-white/30 active:text-white/60"
        >
          <ChevronLeft className="h-5 w-5" />
        </Link>
      </div>

      <div className="relative z-10 flex-1" style={{ minHeight: "50vh" }}>
        {/* "You" dot */}
        <div
          ref={dotRef}
          className="animate-fade-in absolute left-1/2 -translate-x-1/2"
          style={{ top: "14%" }}
        >
          <div className="relative flex flex-col items-center">
            <div
              className="absolute -inset-12 rounded-full"
              style={{
                background:
                  "radial-gradient(circle, rgba(255,255,255,0.06) 0%, transparent 60%)",
              }}
            />
            <div
              className="absolute -inset-5 rounded-full"
              style={{
                border: "1px solid rgba(255,255,255,0.10)",
                animation: "dot-pulse 3s ease-in-out infinite",
              }}
            />
            <div className="h-5 w-5 rounded-full bg-white/90 shadow-[0_0_24px_rgba(255,255,255,0.4)]" />
            <span className="mt-3 text-[11px] font-semibold uppercase tracking-[0.18em] text-white/25">
              New Password
            </span>
          </div>
        </div>

        {/* Field nodes */}
        {FIELDS.map((field, i) => {
          const isActive = activeIdx === i;
          const isFilled = values[i].length > 0;
          const [fcr, fcg, fcb] = field.color;

          return (
            <div
              key={field.key}
              ref={(el) => {
                nodeRefs.current[i] = el;
              }}
              className="absolute"
              style={{
                left: `${field.pos.left}%`,
                top: `${field.pos.top}%`,
                transform: "translate(-50%, -50%)",
                zIndex: 10,
                animation: `fade-in 0.6s cubic-bezier(0.16,1,0.3,1) ${200 + i * 150}ms both`,
              }}
            >
              <div style={{ animation: field.float }}>
                <div
                  onPointerDown={(e) => handleNodePointerDown(e, i)}
                  className="flex cursor-pointer select-none items-center gap-2.5 rounded-full"
                  style={{
                    padding: "8px 16px 8px 10px",
                    background: isActive
                      ? `rgba(${fcr},${fcg},${fcb}, 0.12)`
                      : isFilled
                        ? "rgba(255,255,255,0.03)"
                        : "rgba(255,255,255,0.015)",
                    border: isActive
                      ? `1.5px solid rgba(${fcr},${fcg},${fcb}, 0.35)`
                      : isFilled
                        ? "1.5px solid rgba(255,255,255,0.06)"
                        : "1.5px solid rgba(255,255,255,0.04)",
                    transition:
                      "background 0.3s, border-color 0.3s, box-shadow 0.3s",
                    boxShadow: isActive
                      ? `0 0 28px rgba(${fcr},${fcg},${fcb}, 0.15)`
                      : "none",
                  }}
                >
                  <div className="relative" data-dot>
                    <div
                      className="absolute -inset-1.5 rounded-full"
                      style={{
                        border: `1.5px solid rgba(${fcr},${fcg},${fcb}, ${isActive ? 0.6 : isFilled ? 0.3 : 0.12})`,
                        transform: isActive ? "scale(1.3)" : "scale(1)",
                        transition: "all 0.3s ease",
                      }}
                    />
                    {isFilled && (
                      <div
                        className="absolute -inset-3 rounded-full"
                        style={{
                          background: `radial-gradient(circle, ${field.glow} 0%, transparent 70%)`,
                          opacity: 0.4,
                        }}
                      />
                    )}
                    <div
                      className="h-3 w-3 rounded-full"
                      style={{
                        background: `rgba(${fcr},${fcg},${fcb}, ${isActive || isFilled ? 1 : 0.65})`,
                        boxShadow:
                          isActive || isFilled
                            ? `0 0 12px ${field.glow}`
                            : `0 0 6px rgba(${fcr},${fcg},${fcb}, 0.3)`,
                        transition: "all 0.3s ease",
                      }}
                    />
                  </div>

                  <span
                    className="whitespace-nowrap font-medium"
                    style={{
                      fontSize: 13,
                      color: isActive
                        ? `rgba(${fcr},${fcg},${fcb}, 0.9)`
                        : isFilled
                          ? "rgba(255,255,255,0.50)"
                          : "rgba(255,255,255,0.28)",
                      letterSpacing: isFilled ? "-0.01em" : "0.03em",
                      textTransform: isFilled ? "none" : "uppercase",
                      transition: "color 0.3s",
                    }}
                  >
                    {isFilled
                      ? displayValue(values[i], field.type)
                      : field.label}
                  </span>

                  {isFilled && !isActive && (
                    <svg
                      width="14"
                      height="14"
                      viewBox="0 0 14 14"
                      fill="none"
                      style={{ opacity: 0.35, marginLeft: -2 }}
                    >
                      <circle
                        cx="7"
                        cy="7"
                        r="6"
                        stroke={`rgba(${fcr},${fcg},${fcb}, 0.4)`}
                        strokeWidth="1.2"
                      />
                      <path
                        d="M4.5 7L6.2 8.7L9.5 5.3"
                        stroke={`rgba(${fcr},${fcg},${fcb}, 0.6)`}
                        strokeWidth="1.3"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    </svg>
                  )}
                </div>
              </div>
            </div>
          );
        })}

        {/* Input panel */}
        <div
          className="absolute left-1/2"
          style={{
            top: "72%",
            width: "84%",
            transform: "translate(-50%, -50%)",
            animation: "fade-in 0.4s cubic-bezier(0.16,1,0.3,1) 350ms both",
          }}
        >
          <div
            className="overflow-hidden rounded-2xl"
            style={{
              background: "rgba(255,255,255,0.04)",
              border: `1px solid rgba(${cr},${cg},${cb}, 0.15)`,
              boxShadow: `0 0 40px rgba(${cr},${cg},${cb}, 0.06)`,
              transition: "border-color 0.3s, box-shadow 0.3s",
            }}
          >
            <div className="flex items-center gap-2.5 px-4 pt-3 pb-1">
              <div
                className="h-2 w-2 rounded-full"
                style={{
                  background: `rgba(${cr},${cg},${cb}, 0.7)`,
                  boxShadow: `0 0 6px ${activeField.glow}`,
                  transition: "all 0.3s",
                }}
              />
              <span
                className="text-[10px] font-semibold uppercase tracking-[0.14em]"
                style={{
                  color: `rgba(${cr},${cg},${cb}, 0.5)`,
                  transition: "color 0.3s",
                }}
              >
                {activeField.label}
              </span>
              <span
                className="ml-auto text-[10px] tracking-[0.06em]"
                style={{ color: "rgba(255,255,255,0.14)" }}
              >
                {activeIdx + 1} / {FIELDS.length}
              </span>
            </div>
            <div className="flex items-center px-4 pb-3.5">
              <input
                ref={inputRef}
                type={activeField.type}
                placeholder={activeField.placeholder}
                autoComplete={activeField.autoComplete}
                value={values[activeIdx]}
                onChange={(e) => setValue(activeIdx, e.target.value)}
                onKeyDown={handleInputKeyDown}
                className="flex-1 bg-transparent text-[16px] text-white outline-none placeholder:text-white/15"
                style={{
                  caretColor: `rgba(${cr},${cg},${cb}, 0.7)`,
                }}
              />
              <button
                type="button"
                disabled={loading}
                onPointerDown={(e) => {
                  e.preventDefault();
                  if (activeIdx < FIELDS.length - 1) {
                    setActiveIdx(activeIdx + 1);
                  } else if (allFilled) {
                    handleSubmit();
                  }
                }}
                className="ml-2 flex h-7 w-7 shrink-0 items-center justify-center rounded-full transition-all active:scale-90"
                style={{
                  background: `rgba(${cr},${cg},${cb}, ${isLastField && allFilled ? 0.22 : 0.07})`,
                  border: `1px solid rgba(${cr},${cg},${cb}, ${isLastField && allFilled ? 0.45 : 0.18})`,
                  boxShadow: isLastField && allFilled ? `0 0 12px rgba(${cr},${cg},${cb}, 0.2)` : "none",
                  transition: "all 0.3s cubic-bezier(0.16,1,0.3,1)",
                }}
              >
                {loading ? (
                  <Loader2
                    className="h-3.5 w-3.5 animate-spin"
                    style={{ color: `rgba(${cr},${cg},${cb}, 0.7)` }}
                  />
                ) : (
                  <ChevronRight
                    className="h-3.5 w-3.5"
                    style={{ color: `rgba(${cr},${cg},${cb}, 0.75)` }}
                  />
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Progress dots */}
        <div
          className="absolute left-1/2 -translate-x-1/2 flex items-center gap-2"
          style={{ top: "86%" }}
        >
          {FIELDS.map((field, i) => {
            const [fcr, fcg, fcb] = field.color;
            return (
              <div
                key={field.key}
                className="rounded-full"
                style={{
                  width: activeIdx === i ? 18 : 6,
                  height: 6,
                  background:
                    values[i].length > 0
                      ? `rgba(${fcr},${fcg},${fcb}, 0.7)`
                      : activeIdx === i
                        ? `rgba(${fcr},${fcg},${fcb}, 0.35)`
                        : "rgba(255,255,255,0.10)",
                  borderRadius: 3,
                  transition: "all 0.3s cubic-bezier(0.16,1,0.3,1)",
                }}
              />
            );
          })}
        </div>

        {error && (
          <div
            className="absolute left-1/2 -translate-x-1/2 text-center text-[13px] text-red-400/80"
            style={{ top: "92%" }}
          >
            {error}
          </div>
        )}
      </div>
    </div>
  );
}
