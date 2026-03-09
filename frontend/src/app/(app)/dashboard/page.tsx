"use client";

import { useEffect, useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { api, type ProfileResponse } from "@/lib/api";
import { Aurora } from "@/components/aurora";
import { LogOut, ScanFace, Square } from "lucide-react";
import { SocketClient, type SocketMessage, type ProfileCard } from "@/lib/socket";

function resolvePhotoUrl(photoPath: string | null): string | null {
  if (!photoPath) return null;
  if (photoPath.startsWith("http")) return photoPath;
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
  if (!supabaseUrl) return null;
  return `${supabaseUrl}/storage/v1/object/public/${photoPath}`;
}

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
  const [capturing, setCapturing] = useState(false);
  const [captureLoading, setCaptureLoading] = useState(false);
  const socketRef = useRef<SocketClient | null>(null);
  const mountIdRef = useRef(`dashboard-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`);

  useEffect(() => {
    const supabase = createClient();
    const socket = new SocketClient();
    socketRef.current = socket;
    const mountId = mountIdRef.current;
    console.log("[DashboardSocket] effect mount", { mountId });

    const unsubscribe = socket.onMessage((message) => {
      if (message.type === "recognition_status") {
        const status = message.payload.status;
        if (status === "started") setCapturing(true);
        if (status === "stopping" || status === "stopped") setCapturing(false);
        return;
      }

      if (message.type === "recognition_result") {
        const parsed = parseRecognitionResult(message);
        if (!parsed) return;
        setResults((prev) => upsertRecognitionResult(prev, parsed));
        return;
      }

      if (message.type === "recognition_error") {
        console.error("Recognition error:", message.payload);
      }
    });

    async function init() {
      const {
        data: { session },
      } = await supabase.auth.getSession();
      if (!session) {
        setLoading(false);
        return;
      }

      api.setToken(session.access_token);
      socket.connect();
      setLoading(false);
    }

    void init();
    return () => {
      console.log("[DashboardSocket] effect cleanup", {
        mountId,
        hadSocket: Boolean(socketRef.current),
        wasConnected: socket.isConnected(),
      });
      unsubscribe();
      socket.disconnect();
      socketRef.current = null;
    };
  }, []);

  async function toggleCapture() {
    const socket = socketRef.current;
    if (!socket) return;

    setCaptureLoading(true);
    try {
      if (!socket.isConnected()) socket.connect();
      const connected = await waitForSocketConnection(socket);
      if (!connected) return;

      const sent = socket.send({
        type: capturing ? "stop_recognition" : "start_recognition",
      });
      if (!sent) return;
      if (capturing) setCapturing(false);
    } catch { /* ignore */ }
    setCaptureLoading(false);
  }

  async function handleSignOut() {
    const supabase = createClient();
    await supabase.auth.signOut();
    router.push("/");
    router.refresh();
  }

  return (
    <div className="relative flex min-h-dvh flex-col overflow-hidden">
      {/* Aurora */}
      <div className="absolute inset-0" style={{ opacity: 0.45 }}>
        <Aurora className="h-full w-full" mode="focused" />
      </div>

      {/* Gradient mask */}
      <div
        className="pointer-events-none absolute inset-0"
        style={{
          background: "linear-gradient(to bottom, transparent 20%, oklch(0.07 0.015 270) 55%)",
        }}
      />

      {/* Header */}
      <div className="relative z-10 px-6 pt-14 pb-5">
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

          <button
            onClick={toggleCapture}
            disabled={captureLoading}
            className="flex items-center gap-2 rounded-full px-3 py-1.5 transition-all active:scale-95 disabled:opacity-50"
            style={{
              background: capturing ? "oklch(0.22 0.10 25 / 70%)" : "oklch(1 0 0 / 5%)",
              border: capturing
                ? "1px solid oklch(0.6 0.2 25 / 35%)"
                : "1px solid oklch(1 0 0 / 8%)",
            }}
          >
            {capturing ? (
              <>
                <div className="relative flex h-2 w-2">
                  <div className="absolute inline-flex h-full w-full animate-ping rounded-full bg-red-400 opacity-75" />
                  <div className="relative inline-flex h-2 w-2 rounded-full bg-red-500" />
                </div>
                <span className="text-[11px] font-medium uppercase tracking-[0.12em] text-red-300">
                  Scanning
                </span>
                <Square className="h-3 w-3 text-red-400" />
              </>
            ) : (
              <>
                <ScanFace className="h-3.5 w-3.5 text-white/40" />
                <span className="text-[11px] font-medium uppercase tracking-[0.12em] text-white/30">
                  Scan
                </span>
              </>
            )}
          </button>
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
              <RecognitionCard
                key={result.id}
                result={result}
                index={i}
                onSelect={(r) => {
                  const userId = r.matched_user_id;
                  if (!userId) return;
                  if (r.profile) {
                    sessionStorage.setItem(`profile_cache_${userId}`, JSON.stringify(r.profile));
                  }
                  router.push(`/profile/${userId}`);
                }}
              />
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

// ─── Empty state ──────────────────────────────────────────────────────────────

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
      <p className="mt-2 text-[13px] text-white/15">Results appear here in real-time</p>
    </div>
  );
}

// ─── Recognition card ─────────────────────────────────────────────────────────

function RecognitionCard({
  result,
  index,
  onSelect,
}: {
  result: RecognitionResult;
  index: number;
  onSelect: (result: RecognitionResult) => void;
}) {
  const [imgFailed, setImgFailed] = useState(false);
  const profile = result.profile;
  const name = profile?.full_name ?? "Unknown person";
  const initials = name.split(" ").map((n) => n[0]).join("").slice(0, 2).toUpperCase();
  const confidencePct = result.confidence != null ? Math.round(result.confidence) : null;
  const photoUrl = resolvePhotoUrl(profile?.photo_path ?? null);

  function formatTime(dateStr: string) {
    const date = new Date(dateStr);
    const diffMins = Math.floor((Date.now() - date.getTime()) / 60000);
    if (diffMins < 1) return "just now";
    if (diffMins < 60) return `${diffMins}m ago`;
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    return date.toLocaleDateString();
  }

  return (
    <div
      className="rounded-2xl p-4 cursor-pointer active:scale-[0.98] transition-transform"
      style={{
        background: "rgba(255,255,255,0.07)",
        border: "1px solid rgba(255,255,255,0.12)",
        animation: `fade-in 0.4s cubic-bezier(0.16,1,0.3,1) ${index * 50}ms both`,
      }}
      onClick={() => onSelect(result)}
    >
      <div className="flex items-start gap-3">
        {/* Avatar */}
        {photoUrl && !imgFailed ? (
          <img
            src={photoUrl}
            alt={name}
            className="h-12 w-12 shrink-0 rounded-full object-cover mt-0.5"
            style={{ border: "1px solid rgba(255,255,255,0.10)" }}
            onError={() => setImgFailed(true)}
          />
        ) : (
          <div
            className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full text-[15px] font-medium text-white/60 mt-0.5"
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
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <p className="truncate text-[15px] font-semibold text-white">{name}</p>
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
                <p className="truncate text-[13px] text-white/50 mt-0.5">{profile.headline}</p>
              )}
              {profile?.profile_one_liner && (
                <p className="text-[12px] text-white/35 mt-1.5 leading-snug line-clamp-2">
                  {profile.profile_one_liner}
                </p>
              )}
            </div>
            <p className="shrink-0 text-[11px] text-white/22 pt-0.5">{formatTime(result.created_at)}</p>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function parseRecognitionResult(
  message: Extract<SocketMessage, { type: "recognition_result" }>,
): RecognitionResult | null {
  const match = message.payload.result.matches[0];
  if (!match) return null;

  return {
    id: match.user_id,
    user_id: match.user_id,
    matched_user_id: match.user_id,
    confidence: match.face_similarity,
    created_at: message.payload.timestamp || new Date().toISOString(),
    profile: toProfileResponse(match),
  };
}

function waitForSocketConnection(socket: SocketClient): Promise<boolean> {
  if (socket.isConnected()) return Promise.resolve(true);

  return new Promise((resolve) => {
    let attempts = 0;
    const interval = window.setInterval(() => {
      attempts += 1;
      if (socket.isConnected()) { window.clearInterval(interval); resolve(true); return; }
      if (attempts >= 20) { window.clearInterval(interval); resolve(false); }
    }, 100);
  });
}

function upsertRecognitionResult(
  previous: RecognitionResult[],
  incoming: RecognitionResult,
): RecognitionResult[] {
  const incomingKey = getRecognitionProfileKey(incoming);
  const existingIndex = previous.findIndex((item) => {
    const itemKey = getRecognitionProfileKey(item);
    if (incomingKey && itemKey) return itemKey === incomingKey;
    return item.id === incoming.id;
  });

  if (existingIndex === -1) return [incoming, ...previous].slice(0, 20);
  if (existingIndex === 0) return [incoming, ...previous.slice(1)];
  return [incoming, ...previous.slice(0, existingIndex), ...previous.slice(existingIndex + 1)].slice(0, 20);
}

function getRecognitionProfileKey(result: RecognitionResult): string | null {
  return result.profile?.user_id || result.matched_user_id;
}

function toProfileResponse(match: ProfileCard): ProfileResponse {
  return {
    user_id: match.user_id,
    full_name: match.full_name,
    headline: match.headline,
    bio: match.bio,
    location: match.location,
    company: match.company,
    major: match.major,
    graduation_year: match.graduation_year,
    linkedin_url: match.linkedin_url,
    photo_path: match.photo_path,
    experiences: match.experiences as ProfileResponse["experiences"],
    education: match.education as ProfileResponse["education"],
    profile_one_liner: match.profile_one_liner,
    profile_summary: match.profile_summary,
  };
}
