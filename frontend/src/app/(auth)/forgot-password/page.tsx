"use client";

import { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { Loader2, ChevronLeft, ChevronRight, Mail, CheckCircle } from "lucide-react";
import { Aurora } from "@/components/aurora";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    requestAnimationFrame(() => inputRef.current?.focus());
  }, []);

  async function handleSubmit(e?: React.FormEvent) {
    e?.preventDefault();
    if (!email.trim()) return;

    setError(null);
    setLoading(true);

    try {
      const siteUrl = process.env.NEXT_PUBLIC_SITE_URL ?? window.location.origin;
      const res = await fetch(`${API_URL}/api/v1/auth/reset-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: email.trim(),
          redirect_to: `${siteUrl}/reset-password`,
        }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Something went wrong");
      }

      setSent(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  const color = [100, 75, 240] as const;
  const [cr, cg, cb] = color;

  if (sent) {
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
              background: "rgba(100,75,240,0.12)",
              border: "1.5px solid rgba(100,75,240,0.3)",
            }}
          >
            <CheckCircle className="h-7 w-7 text-[rgba(100,75,240,0.8)]" />
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
            Check your email
          </h1>

          <p className="mb-2 max-w-[280px] text-[15px] leading-relaxed text-white/45">
            We sent a password reset link to
          </p>
          <p className="mb-6 text-[15px] font-medium text-white/70">
            {email}
          </p>
          <p className="mb-8 max-w-[280px] text-[13px] leading-relaxed text-white/30">
            Click the link in the email to set a new password. If you don&apos;t see it, check your spam folder.
          </p>

          <button
            onClick={() => {
              setSent(false);
              setEmail("");
            }}
            className="flex items-center gap-2 rounded-full px-5 py-2.5 text-[13px] font-medium text-white/50 transition-all active:scale-95"
            style={{
              background: "rgba(255,255,255,0.04)",
              border: "1px solid rgba(255,255,255,0.08)",
            }}
          >
            <Mail className="h-3.5 w-3.5" />
            Try a different email
          </button>

          <Link
            href="/login"
            className="mt-8 text-[13px] text-white/25 active:text-white/50"
          >
            Back to sign in
          </Link>
        </div>
      </div>
    );
  }

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

      <div className="animate-fade-in relative z-10 px-6 pt-4">
        <Link
          href="/login"
          className="inline-flex h-[44px] items-center text-white/30 active:text-white/60"
        >
          <ChevronLeft className="h-5 w-5" />
        </Link>
      </div>

      <div className="relative z-10 flex flex-1 flex-col items-center justify-center px-6">
        <div className="w-full max-w-sm">
          <div className="mb-8 text-center">
            <h1
              className="mb-2 text-white"
              style={{
                fontFamily: "var(--font-serif)",
                fontSize: 28,
                fontWeight: 400,
                letterSpacing: "-0.02em",
              }}
            >
              Reset password
            </h1>
            <p className="text-[14px] text-white/40">
              Enter your email and we&apos;ll send you a reset link
            </p>
          </div>

          <form onSubmit={handleSubmit}>
            <div
              className="mb-4 overflow-hidden rounded-2xl"
              style={{
                background: "rgba(255,255,255,0.04)",
                border: `1px solid rgba(${cr},${cg},${cb}, 0.15)`,
                boxShadow: `0 0 40px rgba(${cr},${cg},${cb}, 0.06)`,
              }}
            >
              <div className="flex items-center gap-2.5 px-4 pt-3 pb-1">
                <div
                  className="h-2 w-2 rounded-full"
                  style={{
                    background: `rgba(${cr},${cg},${cb}, 0.7)`,
                    boxShadow: `0 0 6px rgba(${cr},${cg},${cb}, 0.45)`,
                  }}
                />
                <span
                  className="text-[10px] font-semibold uppercase tracking-[0.14em]"
                  style={{ color: `rgba(${cr},${cg},${cb}, 0.5)` }}
                >
                  Email
                </span>
              </div>
              <div className="flex items-center px-4 pb-3.5">
                <input
                  ref={inputRef}
                  type="email"
                  placeholder="you@example.com"
                  autoComplete="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") handleSubmit();
                  }}
                  className="flex-1 bg-transparent text-[16px] text-white outline-none placeholder:text-white/15"
                  style={{ caretColor: `rgba(${cr},${cg},${cb}, 0.7)` }}
                />
                <button
                  type="submit"
                  disabled={!email.trim() || loading}
                  className="ml-2 flex h-7 w-7 shrink-0 items-center justify-center rounded-full transition-all active:scale-90"
                  style={{
                    background: `rgba(${cr},${cg},${cb}, ${email.trim() ? 0.22 : 0.07})`,
                    border: `1px solid rgba(${cr},${cg},${cb}, ${email.trim() ? 0.45 : 0.18})`,
                    boxShadow: email.trim() ? `0 0 12px rgba(${cr},${cg},${cb}, 0.2)` : "none",
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
          </form>

          {error && (
            <p className="mb-4 text-center text-[13px] text-red-400/80">
              {error}
            </p>
          )}

          <p className="text-center text-[12px] text-white/18">
            Remember your password?{" "}
            <Link
              href="/login"
              className="font-semibold text-white/35 active:text-white/60"
            >
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
