"use client";

import { useEffect, useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { api, type ProfileResponse } from "@/lib/api";
import { Aurora } from "@/components/aurora";
import { LogOut } from "lucide-react";

interface RecognitionResult {
  id: string;
  user_id: string;
  matched_user_id: string | null;
  confidence: number | null;
  created_at: string;
  profile?: ProfileResponse;
}

export default function DashboardPage() {
  const router = useRouter();
  const [results, setResults] = useState<RecognitionResult[]>([]);
  const [loading, setLoading] = useState(true);
  const tokenRef = useRef<string | null>(null);

  useEffect(() => {
    const supabase = createClient();

    async function init() {
      const {
        data: { session },
      } = await supabase.auth.getSession();
      if (!session) return;

      const userId = session.user.id;
      tokenRef.current = session.access_token;
      api.setToken(session.access_token);

      // Load recent results
      const { data } = await supabase
        .from("recognition_results")
        .select("*")
        .eq("user_id", userId)
        .order("created_at", { ascending: false })
        .limit(20);

      if (data && data.length > 0) {
        const enriched = await Promise.all(
          data.map(async (r: RecognitionResult) => {
            if (r.matched_user_id) {
              try {
                const profile = await api.getProfileById(r.matched_user_id);
                return { ...r, profile };
              } catch {
                return r;
              }
            }
            return r;
          })
        );
        setResults(enriched);
      }
      setLoading(false);

      // Subscribe to real-time inserts
      const channel = supabase
        .channel("recognition-feed")
        .on(
          "postgres_changes",
          {
            event: "INSERT",
            schema: "public",
            table: "recognition_results",
            filter: `user_id=eq.${userId}`,
          },
          async (payload) => {
            const newResult = payload.new as RecognitionResult;
            let enriched: RecognitionResult = newResult;
            if (newResult.matched_user_id) {
              try {
                const profile = await api.getProfileById(
                  newResult.matched_user_id
                );
                enriched = { ...newResult, profile };
              } catch {
                // show card without profile data
              }
            }
            setResults((prev) => [enriched, ...prev.slice(0, 19)]);
          }
        )
        .subscribe();

      return () => {
        channel.unsubscribe();
      };
    }

    const cleanup = init();
    return () => {
      cleanup.then((fn) => fn?.());
    };
  }, []);

  async function handleSignOut() {
    const supabase = createClient();
    await supabase.auth.signOut();
    router.push("/");
    router.refresh();
  }

  return (
    <div className="relative flex min-h-dvh flex-col overflow-hidden">
      {/* Aurora */}
      <div className="absolute inset-0" style={{ opacity: 0.22 }}>
        <Aurora className="h-full w-full" mode="focused" />
      </div>

      {/* Gradient mask */}
      <div
        className="pointer-events-none absolute inset-0"
        style={{
          background:
            "linear-gradient(to bottom, transparent 20%, oklch(0.04 0.005 270) 55%)",
        }}
      />

      {/* Header */}
      <div className="relative z-10 px-6 pt-14 pb-4">
        <div className="flex items-center justify-between">
          <h1
            className="text-white"
            style={{
              fontFamily: "var(--font-serif)",
              fontSize: 28,
              fontWeight: 400,
              letterSpacing: "-0.02em",
            }}
          >
            Recognition Feed
          </h1>
          <div className="flex items-center gap-2">
            <div className="relative flex h-2 w-2">
              <div className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
              <div className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500" />
            </div>
            <span className="text-[11px] font-medium uppercase tracking-[0.12em] text-white/30">
              Live
            </span>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="relative z-10 flex-1 overflow-y-auto px-6 pb-4">
        {loading ? (
          <div className="flex items-center justify-center py-16">
            <div className="h-6 w-6 animate-spin rounded-full border-2 border-white/10 border-t-white/40" />
          </div>
        ) : results.length === 0 ? (
          <EmptyState />
        ) : (
          <div className="space-y-3">
            {results.map((result, i) => (
              <RecognitionCard key={result.id} result={result} index={i} />
            ))}
          </div>
        )}
      </div>

      {/* Sign out */}
      <div className="relative z-10 px-6 pb-3">
        <button
          onClick={handleSignOut}
          className="flex w-full items-center justify-center gap-2 py-2 text-[13px] text-white/20 active:text-white/40"
        >
          <LogOut className="h-3.5 w-3.5" />
          Sign Out
        </button>
      </div>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      <div className="relative mb-6 flex h-16 w-16 items-center justify-center">
        <div
          className="absolute h-full w-full rounded-full border border-white/10"
          style={{ animation: "recognition-ring 3s ease-out infinite" }}
        />
        <div
          className="absolute h-full w-full scale-75 rounded-full border border-white/[0.06]"
          style={{ animation: "recognition-ring 3s ease-out 1s infinite" }}
        />
        <div className="h-3 w-3 rounded-full bg-white/20" />
      </div>
      <p className="text-[15px] text-white/30">Waiting for recognitions...</p>
      <p className="mt-2 text-[13px] text-white/15">
        Results appear here in real-time
      </p>
    </div>
  );
}

function RecognitionCard({
  result,
  index,
}: {
  result: RecognitionResult;
  index: number;
}) {
  const profile = result.profile;
  const name = profile?.full_name ?? "Unknown person";
  const initials = name
    .split(" ")
    .map((n) => n[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
  const confidencePct =
    result.confidence != null ? Math.round(result.confidence * 100) : null;

  function formatTime(dateStr: string) {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    if (diffMins < 1) return "just now";
    if (diffMins < 60) return `${diffMins}m ago`;
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    return date.toLocaleDateString();
  }

  return (
    <div
      className="rounded-2xl p-4"
      style={{
        background: "rgba(255,255,255,0.04)",
        border: "1px solid rgba(255,255,255,0.07)",
        animation: `fade-in 0.4s cubic-bezier(0.16,1,0.3,1) ${index * 50}ms both`,
      }}
    >
      <div className="flex items-center gap-3">
        {/* Avatar */}
        {profile?.photo_path ? (
          <img
            src={profile.photo_path}
            alt={name}
            className="h-12 w-12 shrink-0 rounded-full object-cover"
            style={{ border: "1px solid rgba(255,255,255,0.10)" }}
          />
        ) : (
          <div
            className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full text-[15px] font-medium text-white/60"
            style={{
              background: "rgba(255,255,255,0.06)",
              border: "1px solid rgba(255,255,255,0.10)",
            }}
          >
            {initials}
          </div>
        )}

        {/* Info */}
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <p className="truncate text-[15px] font-semibold text-white">
              {name}
            </p>
            {confidencePct != null && (
              <span
                className="shrink-0 rounded-full px-2 py-0.5 text-[10px] font-medium"
                style={{
                  background: "oklch(0.35 0.12 275 / 40%)",
                  border: "1px solid oklch(0.5 0.15 275 / 25%)",
                  color: "oklch(0.8 0.1 275)",
                }}
              >
                {confidencePct}%
              </span>
            )}
          </div>
          {profile?.headline && (
            <p className="truncate text-[13px] text-white/50">
              {profile.headline}
            </p>
          )}
        </div>

        {/* Timestamp */}
        <p className="shrink-0 text-[11px] text-white/22">
          {formatTime(result.created_at)}
        </p>
      </div>
    </div>
  );
}
