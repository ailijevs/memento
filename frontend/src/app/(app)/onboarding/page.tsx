"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import {
  api,
  type ProfileResponse,
  type ProfileCompletionResponse,
} from "@/lib/api";
import {
  Loader2,
  CheckCircle2,
  Circle,
  Briefcase,
  GraduationCap,
  MapPin,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { Aurora } from "@/components/aurora";

const OPTIONS = [
  {
    key: "linkedin",
    label: "LinkedIn URL",
    placeholder: "linkedin.com/in/yourname",
    color: [100, 75, 240] as const,
    glow: "rgba(100,75,240,0.45)",
    pos: { left: 27, top: 24 },
    float: "float-1 14s ease-in-out infinite",
  },
  {
    key: "resume",
    label: "Resume",
    placeholder: "PDF or DOCX",
    color: [40, 185, 120] as const,
    glow: "rgba(40,185,120,0.45)",
    pos: { left: 73, top: 30 },
    float: "float-2 16s ease-in-out infinite",
  },
];

function truncate(val: string) {
  if (val.length > 18) return val.slice(0, 17) + "…";
  return val;
}

export default function OnboardingPage() {
  const router = useRouter();
  const [step, setStep] = useState<"import" | "preview">("import");
  const [activeIdx, setActiveIdx] = useState(0);
  const [linkedinUrl, setLinkedinUrl] = useState("");
  const [resumeFile, setResumeFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [profile, setProfile] = useState<ProfileResponse | null>(null);
  const [completion, setCompletion] = useState<ProfileCompletionResponse | null>(null);

  const canvasRef = useRef<HTMLCanvasElement>(null);
  const dotRef = useRef<HTMLDivElement>(null);
  const nodeRefs = useRef<(HTMLDivElement | null)[]>([null, null]);
  const inputRef = useRef<HTMLInputElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Refs for canvas draw loop
  const activeIdxRef = useRef(activeIdx);
  activeIdxRef.current = activeIdx;
  const linkedinUrlRef = useRef(linkedinUrl);
  linkedinUrlRef.current = linkedinUrl;
  const resumeFileRef = useRef(resumeFile);
  resumeFileRef.current = resumeFile;

  const isResume = activeIdx === 1;
  const activeOption = OPTIONS[activeIdx];
  const [cr, cg, cb] = activeOption.color;
  const hasValue = isResume ? resumeFile !== null : linkedinUrl.length > 0;

  // Focus text input when on LinkedIn tab
  useEffect(() => {
    if (!isResume) requestAnimationFrame(() => inputRef.current?.focus());
  }, [activeIdx, isResume]);

  // Constellation canvas
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

      const curActive = activeIdxRef.current;
      const curLinkedin = linkedinUrlRef.current;
      const curResume = resumeFileRef.current;

      for (let i = 0; i < OPTIONS.length; i++) {
        const el = nodeRefs.current[i];
        if (!el) continue;
        const dotEl = el.querySelector("[data-dot]");
        if (!dotEl) continue;
        const dr = dotEl.getBoundingClientRect();
        const nx = dr.left + dr.width / 2 - cRect.left;
        const ny = dr.top + dr.height / 2 - cRect.top;

        const [ocr, ocg, ocb] = OPTIONS[i].color;
        const isActive = curActive === i;
        const isFilled = i === 0 ? curLinkedin.length > 0 : curResume !== null;
        const alpha = isActive ? 0.4 : isFilled ? 0.22 : 0.07;

        const grad = ctx!.createLinearGradient(cx, cy, nx, ny);
        grad.addColorStop(0, `rgba(255,255,255,${alpha * 0.6})`);
        grad.addColorStop(0.35, `rgba(${ocr},${ocg},${ocb},${alpha})`);
        grad.addColorStop(1, `rgba(${ocr},${ocg},${ocb},${alpha * 0.3})`);

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
    setError(null);
    // Clear the other field — user picks one source, not both
    if (idx === 0) setResumeFile(null);
    else setLinkedinUrl("");
  }, []);

  async function handleSubmit() {
    if (isResume) {
      setError("Resume import coming soon — use LinkedIn for now.");
      return;
    }
    setError(null);
    setLoading(true);
    try {
      const supabase = createClient();
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) { setError("Session expired. Please sign in again."); setLoading(false); return; }
      api.setToken(session.access_token);
      const result = await api.onboardFromLinkedIn(linkedinUrl);
      setProfile(result.profile);
      setCompletion(result.completion);
      setStep("preview");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to import profile");
    } finally {
      setLoading(false);
    }
  }

  if (step === "preview" && profile && completion) {
    return (
      <ProfilePreview
        profile={profile}
        completion={completion}
        onBack={() => setStep("import")}
        onContinue={() => router.push("/dashboard")}
      />
    );
  }

  return (
    <div className="relative flex min-h-dvh flex-col overflow-hidden">
      {/* Aurora */}
      <div className="absolute inset-0">
        <Aurora className="h-full w-full" mode="focused" />
      </div>

      {/* Gradient mask — aurora only at top */}
      <div
        className="pointer-events-none absolute inset-0"
        style={{ background: "linear-gradient(to bottom, transparent 15%, oklch(0.04 0.005 270) 50%)" }}
      />

      {/* Constellation canvas */}
      <canvas
        ref={canvasRef}
        className="pointer-events-none absolute inset-0 z-[5]"
        style={{ width: "100%", height: "100%" }}
        aria-hidden="true"
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

      {/* Page header */}
      <div className="relative z-10 px-6 pb-4">
        <p className="mb-2 text-[10px] font-semibold uppercase tracking-[0.18em] text-white/22">
          Step 1 of 2
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
          Build your profile
        </h1>
        <p className="mt-2 text-[14px] leading-relaxed text-white/38">
          Pick a source — we&apos;ll pull in your name, photo, and work history automatically.
        </p>
      </div>

      {/* Constellation area — sources at top, profile dot below */}
      <div className="relative z-10 flex-1" style={{ minHeight: "52vh" }}>

        {/* "Profile" dot — destination at the bottom of the constellation */}
        <div
          ref={dotRef}
          className="absolute left-1/2 -translate-x-1/2"
          style={{ top: "58%" }}
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
            <span className="mt-3 text-[11px] font-semibold uppercase tracking-[0.18em] text-white/25">Profile</span>
          </div>
        </div>

        {/* Option nodes */}
        {OPTIONS.map((opt, i) => {
          const isActive = activeIdx === i;
          const isFilled = i === 0 ? linkedinUrl.length > 0 : resumeFile !== null;
          const [ocr, ocg, ocb] = opt.color;
          const displayVal = i === 0 ? truncate(linkedinUrl) : truncate(resumeFile?.name ?? "");

          return (
            <div
              key={opt.key}
              ref={(el) => { nodeRefs.current[i] = el; }}
              className="absolute"
              style={{
                left: `${opt.pos.left}%`,
                top: `${opt.pos.top}%`,
                transform: "translate(-50%, -50%)",
                zIndex: 10,
                animation: `fade-in 0.6s cubic-bezier(0.16,1,0.3,1) ${200 + i * 150}ms both`,
              }}
            >
              <div style={{ animation: opt.float }}>
                <div
                  onPointerDown={(e) => handleNodePointerDown(e, i)}
                  className="flex cursor-pointer select-none items-center gap-2.5 rounded-full"
                  style={{
                    padding: "8px 16px 8px 10px",
                    background: isActive ? `rgba(${ocr},${ocg},${ocb},0.12)` : isFilled ? "rgba(255,255,255,0.03)" : "rgba(255,255,255,0.015)",
                    border: isActive ? `1.5px solid rgba(${ocr},${ocg},${ocb},0.35)` : isFilled ? "1.5px solid rgba(255,255,255,0.06)" : "1.5px solid rgba(255,255,255,0.04)",
                    transition: "background 0.3s, border-color 0.3s, box-shadow 0.3s",
                    boxShadow: isActive ? `0 0 28px rgba(${ocr},${ocg},${ocb},0.15)` : "none",
                  }}
                >
                  <div className="relative" data-dot>
                    <div
                      className="absolute -inset-1.5 rounded-full"
                      style={{
                        border: `1.5px solid rgba(${ocr},${ocg},${ocb},${isActive ? 0.6 : isFilled ? 0.3 : 0.12})`,
                        transform: isActive ? "scale(1.3)" : "scale(1)",
                        transition: "all 0.3s ease",
                      }}
                    />
                    {isFilled && (
                      <div
                        className="absolute -inset-3 rounded-full"
                        style={{ background: `radial-gradient(circle, ${opt.glow} 0%, transparent 70%)`, opacity: 0.4 }}
                      />
                    )}
                    <div
                      className="h-3 w-3 rounded-full"
                      style={{
                        background: `rgba(${ocr},${ocg},${ocb},${isActive || isFilled ? 1 : 0.65})`,
                        boxShadow: isActive || isFilled ? `0 0 12px ${opt.glow}` : `0 0 6px rgba(${ocr},${ocg},${ocb},0.3)`,
                        transition: "all 0.3s ease",
                      }}
                    />
                  </div>

                  <div className="flex flex-col gap-0.5">
                    <span
                      className="whitespace-nowrap font-medium leading-tight"
                      style={{
                        fontSize: 13,
                        color: isActive ? `rgba(${ocr},${ocg},${ocb},0.9)` : isFilled ? "rgba(255,255,255,0.50)" : "rgba(255,255,255,0.28)",
                        letterSpacing: isFilled ? "-0.01em" : "0.03em",
                        textTransform: isFilled ? "none" : "uppercase",
                        transition: "color 0.3s",
                      }}
                    >
                      {isFilled ? displayVal : opt.label}
                    </span>
                    {/* "coming soon" badge on resume node */}
                    {i === 1 && (
                      <span
                        style={{
                          fontSize: 9,
                          letterSpacing: "0.08em",
                          textTransform: "uppercase",
                          color: `rgba(${ocr},${ocg},${ocb},0.45)`,
                        }}
                      >
                        coming soon
                      </span>
                    )}
                  </div>

                  {isFilled && !isActive && (
                    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" style={{ opacity: 0.35, marginLeft: -2 }}>
                      <circle cx="7" cy="7" r="6" stroke={`rgba(${ocr},${ocg},${ocb},0.4)`} strokeWidth="1.2" />
                      <path d="M4.5 7L6.2 8.7L9.5 5.3" stroke={`rgba(${ocr},${ocg},${ocb},0.6)`} strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" />
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
            top: "84%",
            width: "84%",
            transform: "translate(-50%, -50%)",
            animation: "fade-in 0.4s cubic-bezier(0.16,1,0.3,1) 350ms both",
          }}
        >
          <div
            className="overflow-hidden rounded-2xl"
            style={{
              background: "rgba(255,255,255,0.04)",
              border: `1px solid rgba(${cr},${cg},${cb},0.15)`,
              boxShadow: `0 0 40px rgba(${cr},${cg},${cb},0.06)`,
              transition: "border-color 0.3s, box-shadow 0.3s",
            }}
          >
            <div className="flex items-center gap-2.5 px-4 pt-3 pb-1">
              <div
                className="h-2 w-2 rounded-full"
                style={{ background: `rgba(${cr},${cg},${cb},0.7)`, boxShadow: `0 0 6px ${activeOption.glow}`, transition: "all 0.3s" }}
              />
              <span
                className="text-[10px] font-semibold uppercase tracking-[0.14em]"
                style={{ color: `rgba(${cr},${cg},${cb},0.5)`, transition: "color 0.3s" }}
              >
                {activeOption.label}
              </span>
            </div>

            <div className="flex items-center px-4 pb-3.5">
              {isResume ? (
                <>
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    className="flex-1 text-left text-[16px] outline-none"
                    style={{ color: resumeFile ? "rgba(255,255,255,0.85)" : "rgba(255,255,255,0.15)" }}
                  >
                    {resumeFile ? truncate(resumeFile.name) : activeOption.placeholder}
                  </button>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".pdf,.docx,.doc"
                    className="hidden"
                    onChange={(e) => { setResumeFile(e.target.files?.[0] ?? null); setError(null); }}
                  />
                  <button
                    type="button"
                    onPointerDown={(e) => { e.preventDefault(); fileInputRef.current?.click(); }}
                    className="ml-2 shrink-0 flex h-7 w-7 items-center justify-center rounded-full transition-all active:scale-90"
                    style={{
                      background: `rgba(${cr},${cg},${cb},0.07)`,
                      border: `1px solid rgba(${cr},${cg},${cb},0.18)`,
                    }}
                  >
                    <ChevronRight className="h-3.5 w-3.5" style={{ color: `rgba(${cr},${cg},${cb},0.75)` }} />
                  </button>
                </>
              ) : (
                <>
                  <input
                    ref={inputRef}
                    type="url"
                    placeholder={activeOption.placeholder}
                    autoComplete="url"
                    value={linkedinUrl}
                    onChange={(e) => setLinkedinUrl(e.target.value)}
                    onKeyDown={(e) => { if (e.key === "Enter" && hasValue) handleSubmit(); }}
                    className="flex-1 bg-transparent text-[16px] text-white outline-none placeholder:text-white/15"
                    style={{ caretColor: `rgba(${cr},${cg},${cb},0.7)` }}
                  />
                  <button
                    type="button"
                    onPointerDown={(e) => { e.preventDefault(); if (hasValue) handleSubmit(); }}
                    className="ml-2 shrink-0 flex h-7 w-7 items-center justify-center rounded-full transition-all active:scale-90"
                    style={{
                      background: `rgba(${cr},${cg},${cb},${hasValue ? 0.22 : 0.07})`,
                      border: `1px solid rgba(${cr},${cg},${cb},${hasValue ? 0.45 : 0.18})`,
                      boxShadow: hasValue ? `0 0 12px rgba(${cr},${cg},${cb},0.2)` : "none",
                      transition: "all 0.3s cubic-bezier(0.16,1,0.3,1)",
                    }}
                  >
                    {loading ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" style={{ color: `rgba(${cr},${cg},${cb},0.7)` }} />
                    ) : (
                      <ChevronRight className="h-3.5 w-3.5" style={{ color: `rgba(${cr},${cg},${cb},0.75)` }} />
                    )}
                  </button>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Progress dots */}
        <div className="absolute left-1/2 -translate-x-1/2 flex items-center gap-2" style={{ top: "97%" }}>
          {OPTIONS.map((opt, i) => {
            const [ocr, ocg, ocb] = opt.color;
            const isFilled = i === 0 ? linkedinUrl.length > 0 : resumeFile !== null;
            return (
              <div
                key={opt.key}
                className="rounded-full"
                style={{
                  width: activeIdx === i ? 18 : 6,
                  height: 6,
                  background: isFilled ? `rgba(${ocr},${ocg},${ocb},0.7)` : activeIdx === i ? `rgba(${ocr},${ocg},${ocb},0.35)` : "rgba(255,255,255,0.10)",
                  borderRadius: 3,
                  transition: "all 0.3s cubic-bezier(0.16,1,0.3,1)",
                }}
              />
            );
          })}
        </div>
      </div>

      {/* Submit button */}
      <div
        className="relative z-10 px-6 pb-3"
        style={{
          opacity: hasValue ? 1 : 0,
          transition: "opacity 0.3s ease",
          pointerEvents: hasValue ? "auto" : "none",
        }}
      >
        <button
          type="button"
          onClick={handleSubmit}
          disabled={loading}
          className="flex h-[56px] w-full items-center justify-center gap-2 rounded-[16px] text-[15px] font-semibold tracking-[-0.01em] text-white/90 transition-all active:scale-[0.98]"
          style={{
            background: "oklch(1 0 0 / 6%)",
            boxShadow: "inset 0 0 0 1px oklch(0.5 0.15 275 / 25%), 0 0 30px oklch(0.4 0.12 275 / 15%)",
          }}
        >
          {loading ? (
            <Loader2 className="h-4 w-4 animate-spin text-white/60" />
          ) : isResume ? (
            "Coming Soon"
          ) : (
            "Import Profile"
          )}
        </button>
        {error && <p className="mt-2 text-center text-[13px] text-red-400/80">{error}</p>}
      </div>

      <div className="relative z-10 h-4" />
    </div>
  );
}

// ─────────────────────────────────────────
// Profile preview
// ─────────────────────────────────────────
function ProfilePreview({
  profile,
  completion,
  onBack,
  onContinue,
}: {
  profile: ProfileResponse;
  completion: ProfileCompletionResponse;
  onBack: () => void;
  onContinue: () => void;
}) {
  return (
    <div className="relative flex min-h-dvh flex-col px-6 pt-4 pb-8 overflow-hidden">
      <div className="absolute inset-0">
        <Aurora className="h-full w-full" mode="focused" />
      </div>

      {/* Back */}
      <div className="relative z-10">
        <button
          onClick={onBack}
          className="inline-flex h-[44px] items-center text-white/30 active:text-white/60"
        >
          <ChevronLeft className="h-5 w-5" />
        </button>
      </div>

      {/* Header */}
      <div className="animate-fade-up relative z-10 mb-8">
        <h1 className="text-large-title text-white">Looking good</h1>
        <p className="text-callout mt-2 text-white/40">
          This is how you&apos;ll appear to others
        </p>
      </div>

      {/* Scrollable content */}
      <div className="relative z-10 flex-1 overflow-y-auto">
        {/* Profile Card */}
        <div className="animate-scale-up delay-200 mb-5 rounded-[20px] bg-white/[0.04] p-6 ring-1 ring-white/[0.06]">
          <div className="flex items-start gap-4">
            {profile.photo_path ? (
              <img
                src={profile.photo_path}
                alt={profile.full_name}
                className="h-[72px] w-[72px] shrink-0 rounded-full object-cover ring-2 ring-white/[0.08]"
              />
            ) : (
              <div className="flex h-[72px] w-[72px] shrink-0 items-center justify-center rounded-full bg-white/[0.06] text-title1 text-white/40">
                {profile.full_name.charAt(0)}
              </div>
            )}
            <div className="min-w-0 pt-1">
              <h2 className="text-title3 truncate text-white">{profile.full_name}</h2>
              {profile.headline && (
                <p className="text-subhead mt-0.5 text-white/50 line-clamp-2">{profile.headline}</p>
              )}
              {profile.location && (
                <div className="text-caption1 mt-2 flex items-center gap-1.5 text-white/25">
                  <MapPin className="h-3 w-3" />
                  {profile.location}
                </div>
              )}
            </div>
          </div>

          {profile.bio && (
            <>
              <div className="my-5 h-px bg-white/[0.06]" />
              <p className="text-subhead leading-[1.6] text-white/40">{profile.bio}</p>
            </>
          )}

          {profile.experiences && profile.experiences.length > 0 && (
            <>
              <div className="my-5 h-px bg-white/[0.06]" />
              <div className="space-y-3">
                <h3 className="text-caption1 flex items-center gap-2 font-medium uppercase tracking-[0.1em] text-white/20">
                  <Briefcase className="h-3 w-3" />
                  Experience
                </h3>
                {profile.experiences.slice(0, 3).map((exp, i) => (
                  <div key={i}>
                    <p className="text-subhead font-medium text-white/70">{exp.title}</p>
                    <p className="text-footnote text-white/30">{exp.company}</p>
                  </div>
                ))}
              </div>
            </>
          )}

          {profile.education && profile.education.length > 0 && (
            <>
              <div className="my-5 h-px bg-white/[0.06]" />
              <div className="space-y-3">
                <h3 className="text-caption1 flex items-center gap-2 font-medium uppercase tracking-[0.1em] text-white/20">
                  <GraduationCap className="h-3 w-3" />
                  Education
                </h3>
                {profile.education.slice(0, 2).map((edu, i) => (
                  <div key={i}>
                    <p className="text-subhead font-medium text-white/70">{edu.school}</p>
                    <p className="text-footnote text-white/30">
                      {[edu.degree, edu.field_of_study].filter(Boolean).join(", ")}
                    </p>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>

        {/* Completion */}
        <div className="animate-fade-up delay-400 rounded-[20px] bg-white/[0.04] p-5 ring-1 ring-white/[0.06]">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="text-headline text-white/60">Completeness</h3>
            <span className="text-headline memento-gradient-text">
              {completion.completion_percentage}%
            </span>
          </div>

          <div className="mb-5 h-[5px] overflow-hidden rounded-full bg-white/[0.04]">
            <div
              className="memento-gradient h-full rounded-full transition-all duration-1000 ease-out"
              style={{
                width: `${completion.completion_percentage}%`,
                ...(completion.completion_percentage === 100
                  ? { background: "linear-gradient(90deg, oklch(0.6 0.18 155), oklch(0.65 0.15 165))" }
                  : {}),
              }}
            />
          </div>

          <div className="grid grid-cols-2 gap-x-4 gap-y-3">
            {completion.filled_fields.map((field) => (
              <div key={field} className="text-footnote flex items-center gap-2 text-white/40">
                <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-400/70" />
                <span className="capitalize">{field.replace(/_/g, " ")}</span>
              </div>
            ))}
            {completion.missing_fields.map((field) => (
              <div key={field} className="text-footnote flex items-center gap-2 text-white/15">
                <Circle className="h-4 w-4 shrink-0" />
                <span className="capitalize">{field.replace(/_/g, " ")}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Bottom action */}
      <div className="animate-fade-up delay-600 relative z-10 pt-6">
        <button
          className="flex h-[56px] w-full items-center justify-center rounded-[16px] text-body font-semibold text-white/90 transition-all active:scale-[0.98] active:bg-white/[0.08]"
          style={{
            background: "oklch(1 0 0 / 5%)",
            boxShadow: "inset 0 0 0 1px oklch(0.5 0.15 275 / 20%), 0 0 30px oklch(0.4 0.12 275 / 12%)",
          }}
          onClick={onContinue}
        >
          Continue
        </button>
      </div>
    </div>
  );
}
