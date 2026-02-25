"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { Glasses, LogOut, Check } from "lucide-react";

export default function DashboardPage() {
  const router = useRouter();
  const [email, setEmail] = useState<string | null>(null);

  useEffect(() => {
    const supabase = createClient();
    supabase.auth.getUser().then(({ data: { user } }) => {
      setEmail(user?.email ?? null);
    });
  }, []);

  async function handleSignOut() {
    const supabase = createClient();
    await supabase.auth.signOut();
    router.push("/");
    router.refresh();
  }

  return (
    <div className="relative flex min-h-dvh flex-col items-center px-6 overflow-hidden">
      {/* Gradient orb — smaller, success-tinted */}
      <div
        className="absolute left-1/2 top-[20%] h-[300px] w-[300px] -translate-x-1/2 rounded-full opacity-15"
        style={{
          background: "conic-gradient(from 180deg, oklch(0.5 0.15 160), oklch(0.5 0.18 270), oklch(0.5 0.15 160))",
          filter: "blur(80px)",
        }}
      />

      {/* Center content */}
      <div className="relative z-10 flex flex-1 flex-col items-center justify-center text-center">
        {/* Logo with check */}
        <div className="animate-scale-up relative mb-10">
          <div className="flex h-[96px] w-[96px] items-center justify-center rounded-[26px] bg-white/[0.06] ring-1 ring-white/[0.08]">
            <Glasses className="h-11 w-11 text-white/80" strokeWidth={1.5} />
          </div>
          <div className="absolute -bottom-1 -right-1 flex h-8 w-8 items-center justify-center rounded-full bg-emerald-500 ring-[3px] ring-[oklch(0.065_0.005_280)]">
            <Check className="h-4 w-4 text-white" strokeWidth={3} />
          </div>
        </div>

        <h1 className="animate-fade-up delay-100 text-title1 text-white">
          You&apos;re all set
        </h1>

        <p className="animate-fade-up delay-200 text-callout mt-3 max-w-[260px] leading-[1.6] text-white/40">
          Your profile is ready. When you attend an event with smart glasses,
          people will see who you are.
        </p>

        {email && (
          <p className="animate-fade-in delay-300 text-caption1 mt-6 text-white/15">{email}</p>
        )}
      </div>

      {/* Bottom */}
      <div className="animate-fade-up delay-400 relative z-10 w-full pb-10">
        <div className="mb-4 rounded-[16px] bg-white/[0.03] px-5 py-4 text-center ring-1 ring-white/[0.04]">
          <p className="text-subhead text-white/25">
            Events, directory, and more — coming soon.
          </p>
        </div>

        <button
          className="flex h-[50px] w-full items-center justify-center gap-2 rounded-[16px] text-body text-white/25 transition-colors active:text-white/50"
          onClick={handleSignOut}
        >
          <LogOut className="h-[18px] w-[18px]" />
          Sign Out
        </button>
      </div>
    </div>
  );
}
