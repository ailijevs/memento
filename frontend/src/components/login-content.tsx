"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { Loader2, ChevronLeft, ChevronRight } from "lucide-react";

const FIELDS = [
  {
    key: "email",
    label: "Email",
    type: "email" as const,
    placeholder: "you@example.com",
    autoComplete: "email",
    color: [100, 75, 240] as const,
    glow: "rgba(100,75,240,0.45)",
    pos: { left: 24, top: 40 },
    float: "float-2 15s ease-in-out infinite",
  },
  {
    key: "password",
    label: "Password",
    type: "password" as const,
    placeholder: "Your password",
    autoComplete: "current-password",
    color: [70, 110, 230] as const,
    glow: "rgba(70,110,230,0.45)",
    pos: { left: 68, top: 52 },
    float: "float-3 14s ease-in-out infinite",
  },
];

function displayValue(val: string, type: string) {
  if (!val) return "";
  if (type === "password") return "••••••";
  if (val.length > 16) return val.slice(0, 15) + "…";
  return val;
}

export function LoginContent({ onBack, onGoSignup, showYouDot = true }: { onBack: () => void; onGoSignup: () => void; showYouDot?: boolean }) {
  const router = useRouter();
  const [values, setValues] = useState(["", ""]);
  const [activeIdx, setActiveIdx] = useState<number>(0);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [googleLoading, setGoogleLoading] = useState(false);

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

  const handleNodePointerDown = useCallback((e: React.PointerEvent, idx: number) => {
    e.preventDefault();
    setActiveIdx(idx);
  }, []);

  const handleInputKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter") {
        e.preventDefault();
        if (activeIdx < FIELDS.length - 1) setActiveIdx(activeIdx + 1);
        else if (allFilled) handleSubmit();
      }
      if (e.key === "Escape") inputRef.current?.blur();
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [activeIdx, allFilled],
  );

  const setValue = useCallback((idx: number, val: string) => {
    setValues((prev) => prev.map((v, i) => (i === idx ? val : v)));
  }, []);

  async function handleSubmit() {
    setError(null);
    setLoading(true);
    const supabase = createClient();
    const { error } = await supabase.auth.signInWithPassword({
      email: values[0],
      password: values[1],
    });
    if (error) { setError(error.message); setLoading(false); return; }
    router.push("/onboarding");
    router.refresh();
  }

  async function handleGoogle() {
    setError(null);
    setGoogleLoading(true);
    const supabase = createClient();
    const { error } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: { redirectTo: `${window.location.origin}/auth/callback` },
    });
    if (error) { setError(error.message); setGoogleLoading(false); }
  }

  const activeField = FIELDS[activeIdx];
  const [cr, cg, cb] = activeField.color;

  return (
    <>
      {/* Constellation canvas */}
      <canvas
        ref={canvasRef}
        className="pointer-events-none absolute inset-0 z-[5]"
        style={{ width: "100%", height: "100%" }}
        aria-hidden="true"
      />

      {/* Back */}
      <div className="animate-fade-in relative z-10 px-6 pt-4">
        <button
          onClick={onBack}
          className="inline-flex h-[44px] items-center text-white/30 active:text-white/60"
        >
          <ChevronLeft className="h-5 w-5" />
        </button>
      </div>

      {/* Constellation area */}
      <div className="relative z-10 flex-1" style={{ minHeight: "50vh" }}>
        {/* "You" dot */}
        <div
          ref={dotRef}
          className="absolute left-1/2 -translate-x-1/2"
          style={{ top: "14%", opacity: showYouDot ? 1 : 0, transition: "opacity 0.3s ease" }}
        >
          <div className="relative flex flex-col items-center">
            <div
              className="absolute -inset-12 rounded-full"
              style={{ background: "radial-gradient(circle, rgba(255,255,255,0.06) 0%, transparent 60%)" }}
            />
            <div
              className="absolute -inset-5 rounded-full"
              style={{ border: "1px solid rgba(255,255,255,0.10)", animation: "dot-pulse 3s ease-in-out infinite" }}
            />
            <div className="h-5 w-5 rounded-full bg-white/90 shadow-[0_0_24px_rgba(255,255,255,0.4)]" />
            <span className="mt-3 text-[11px] font-semibold uppercase tracking-[0.18em] text-white/25">You</span>
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
              ref={(el) => { nodeRefs.current[i] = el; }}
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
                    background: isActive ? `rgba(${fcr},${fcg},${fcb}, 0.12)` : isFilled ? "rgba(255,255,255,0.03)" : "rgba(255,255,255,0.015)",
                    border: isActive ? `1.5px solid rgba(${fcr},${fcg},${fcb}, 0.35)` : isFilled ? "1.5px solid rgba(255,255,255,0.06)" : "1.5px solid rgba(255,255,255,0.04)",
                    transition: "background 0.3s, border-color 0.3s, box-shadow 0.3s",
                    boxShadow: isActive ? `0 0 28px rgba(${fcr},${fcg},${fcb}, 0.15)` : "none",
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
                        style={{ background: `radial-gradient(circle, ${field.glow} 0%, transparent 70%)`, opacity: 0.4 }}
                      />
                    )}
                    <div
                      className="h-3 w-3 rounded-full"
                      style={{
                        background: `rgba(${fcr},${fcg},${fcb}, ${isActive || isFilled ? 1 : 0.65})`,
                        boxShadow: isActive || isFilled ? `0 0 12px ${field.glow}` : `0 0 6px rgba(${fcr},${fcg},${fcb}, 0.3)`,
                        transition: "all 0.3s ease",
                      }}
                    />
                  </div>
                  <span
                    className="whitespace-nowrap font-medium"
                    style={{
                      fontSize: 13,
                      color: isActive ? `rgba(${fcr},${fcg},${fcb}, 0.9)` : isFilled ? "rgba(255,255,255,0.50)" : "rgba(255,255,255,0.28)",
                      letterSpacing: isFilled ? "-0.01em" : "0.03em",
                      textTransform: isFilled ? "none" : "uppercase",
                      transition: "color 0.3s",
                    }}
                  >
                    {isFilled ? displayValue(values[i], field.type) : field.label}
                  </span>
                  {isFilled && !isActive && (
                    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" style={{ opacity: 0.35, marginLeft: -2 }}>
                      <circle cx="7" cy="7" r="6" stroke={`rgba(${fcr},${fcg},${fcb}, 0.4)`} strokeWidth="1.2" />
                      <path d="M4.5 7L6.2 8.7L9.5 5.3" stroke={`rgba(${fcr},${fcg},${fcb}, 0.6)`} strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" />
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
                style={{ background: `rgba(${cr},${cg},${cb}, 0.7)`, boxShadow: `0 0 6px ${activeField.glow}`, transition: "all 0.3s" }}
              />
              <span
                className="text-[10px] font-semibold uppercase tracking-[0.14em]"
                style={{ color: `rgba(${cr},${cg},${cb}, 0.5)`, transition: "color 0.3s" }}
              >
                {activeField.label}
              </span>
              <span className="ml-auto text-[10px] tracking-[0.06em]" style={{ color: "rgba(255,255,255,0.14)" }}>
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
                style={{ caretColor: `rgba(${cr},${cg},${cb}, 0.7)` }}
              />
              <button
                type="button"
                onPointerDown={(e) => {
                  e.preventDefault();
                  if (activeIdx < FIELDS.length - 1) setActiveIdx(activeIdx + 1);
                  else if (allFilled) handleSubmit();
                }}
                className="ml-2 shrink-0 flex h-7 w-7 items-center justify-center rounded-full transition-all active:scale-90"
                style={{
                  background: `rgba(${cr},${cg},${cb}, ${isLastField && allFilled ? 0.22 : 0.07})`,
                  border: `1px solid rgba(${cr},${cg},${cb}, ${isLastField && allFilled ? 0.45 : 0.18})`,
                  boxShadow: isLastField && allFilled ? `0 0 12px rgba(${cr},${cg},${cb}, 0.2)` : "none",
                  transition: "all 0.3s cubic-bezier(0.16,1,0.3,1)",
                }}
              >
                {loading ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" style={{ color: `rgba(${cr},${cg},${cb}, 0.7)` }} />
                ) : (
                  <ChevronRight className="h-3.5 w-3.5" style={{ color: `rgba(${cr},${cg},${cb}, 0.75)` }} />
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Progress dots */}
        <div className="absolute left-1/2 -translate-x-1/2 flex items-center gap-2" style={{ top: "86%" }}>
          {FIELDS.map((field, i) => {
            const [fcr, fcg, fcb] = field.color;
            return (
              <div
                key={field.key}
                className="rounded-full"
                style={{
                  width: activeIdx === i ? 18 : 6,
                  height: 6,
                  background: values[i].length > 0 ? `rgba(${fcr},${fcg},${fcb}, 0.7)` : activeIdx === i ? `rgba(${fcr},${fcg},${fcb}, 0.35)` : "rgba(255,255,255,0.10)",
                  borderRadius: 3,
                  transition: "all 0.3s cubic-bezier(0.16,1,0.3,1)",
                }}
              />
            );
          })}
        </div>

        {error && (
          <div className="absolute left-1/2 -translate-x-1/2 text-center text-[13px] text-red-400/80" style={{ top: "92%" }}>
            {error}
          </div>
        )}
      </div>

      {/* Google + footer */}
      <div className="relative z-10 px-6 pb-8">
        <div className="mb-4 flex items-center gap-4">
          <div className="h-px flex-1 bg-white/[0.05]" />
          <span className="text-[10px] uppercase tracking-[0.1em] text-white/14">or</span>
          <div className="h-px flex-1 bg-white/[0.05]" />
        </div>
        <button
          type="button"
          className="flex h-[50px] w-full items-center justify-center gap-3 rounded-[14px] bg-white/[0.03] text-[14px] text-white/50 ring-1 ring-white/[0.05] transition-all active:scale-[0.98] active:bg-white/[0.06]"
          onClick={handleGoogle}
          disabled={googleLoading}
        >
          {googleLoading ? <Loader2 className="h-5 w-5 animate-spin text-white/30" /> : <GoogleIcon />}
          Continue with Google
        </button>
        <p className="mt-5 text-center text-[12px] text-white/18">
          New here?{" "}
          <button onClick={onGoSignup} className="font-semibold text-white/35 active:text-white/60">
            Create an account
          </button>
        </p>
      </div>
    </>
  );
}

function GoogleIcon() {
  return (
    <svg className="h-[18px] w-[18px]" viewBox="0 0 24 24">
      <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4" />
      <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
      <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05" />
      <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
    </svg>
  );
}
