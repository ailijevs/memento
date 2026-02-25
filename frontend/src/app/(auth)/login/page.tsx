"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { Loader2, ChevronLeft } from "lucide-react";
import { NetworkField } from "@/components/network-field";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [googleLoading, setGoogleLoading] = useState(false);

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);

    const supabase = createClient();
    const { error } = await supabase.auth.signInWithPassword({ email, password });

    if (error) {
      setError(error.message);
      setLoading(false);
      return;
    }

    router.push("/onboarding");
    router.refresh();
  }

  async function handleGoogleLogin() {
    setError(null);
    setGoogleLoading(true);

    const supabase = createClient();
    const { error } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: { redirectTo: `${window.location.origin}/auth/callback` },
    });

    if (error) {
      setError(error.message);
      setGoogleLoading(false);
    }
  }

  return (
    <div className="relative flex min-h-dvh flex-col px-6 overflow-hidden">
      <div className="absolute inset-0">
        <NetworkField className="h-full w-full" />
      </div>
      <div
        className="pointer-events-none absolute inset-0"
        style={{
          background: "radial-gradient(ellipse at 55% 30%, oklch(0.08 0.008 270) 0%, transparent 60%)",
        }}
        aria-hidden
      />

      {/* Back */}
      <div className="animate-fade-in relative z-10 pt-4">
        <Link
          href="/"
          className="inline-flex h-[44px] items-center text-white/35 active:text-white/60"
        >
          <ChevronLeft className="h-5 w-5" />
        </Link>
      </div>

      {/* Form */}
      <div className="relative z-10 my-auto w-full">
        <div className="animate-fade-up mb-10">
          <h1 className="text-large-title text-white">Welcome back</h1>
          <p className="text-callout mt-2 text-white/35">
            Sign in to continue
          </p>
        </div>

        <button
          type="button"
          className="animate-fade-up delay-100 flex h-[56px] w-full items-center justify-center gap-3 rounded-[16px] bg-white/[0.05] text-body text-white/80 ring-1 ring-white/[0.07] transition-all active:scale-[0.98] active:bg-white/[0.08]"
          onClick={handleGoogleLogin}
          disabled={googleLoading}
        >
          {googleLoading ? (
            <Loader2 className="h-5 w-5 animate-spin text-white/40" />
          ) : (
            <GoogleIcon />
          )}
          Continue with Google
        </button>

        <div className="animate-fade-in delay-200 my-8 flex items-center gap-4">
          <div className="h-px flex-1 bg-white/[0.06]" />
          <span className="text-caption1 text-white/20">or</span>
          <div className="h-px flex-1 bg-white/[0.06]" />
        </div>

        <form onSubmit={handleLogin} className="animate-fade-up delay-200 flex flex-col gap-4">
          <div>
            <label htmlFor="email" className="mb-2 block text-footnote text-white/35">
              Email
            </label>
            <input
              id="email"
              type="email"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="email"
              className="h-[52px] w-full rounded-[14px] bg-white/[0.04] px-4 text-body text-white outline-none ring-1 ring-white/[0.07] transition-all placeholder:text-white/20 focus:bg-white/[0.06] focus:ring-white/[0.14]"
            />
          </div>

          <div>
            <label htmlFor="password" className="mb-2 block text-footnote text-white/35">
              Password
            </label>
            <input
              id="password"
              type="password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="current-password"
              className="h-[52px] w-full rounded-[14px] bg-white/[0.04] px-4 text-body text-white outline-none ring-1 ring-white/[0.07] transition-all placeholder:text-white/20 focus:bg-white/[0.06] focus:ring-white/[0.14]"
            />
          </div>

          {error && <p className="text-footnote text-red-400/80">{error}</p>}

          <button
            type="submit"
            className="btn-gradient mt-2 h-[56px] w-full rounded-[16px] text-body font-semibold"
            disabled={loading}
          >
            {loading ? <Loader2 className="mx-auto h-5 w-5 animate-spin" /> : "Sign In"}
          </button>
        </form>
      </div>

      <div className="animate-fade-in delay-400 relative z-10 pb-10 pt-8 text-center">
        <p className="text-subhead text-white/25">
          New here?{" "}
          <Link href="/signup" className="font-semibold text-white/50 active:text-white/80">
            Create an account
          </Link>
        </p>
      </div>
    </div>
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
