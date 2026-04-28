"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import {
  api,
  isApiErrorWithStatus,
  type ConsentResponse,
  type ProfileResponse,
  type CompatibilityResponse,
} from "@/lib/api";
import { getCachedEventConsent, setCachedEventConsent } from "@/lib/consent-cache";
import { Aurora } from "@/components/aurora";
import { signOutUser } from "@/lib/signout";
import { Camera, Heart, LogOut, ScanFace, Square } from "lucide-react";
import { SocketClient, type SocketMessage, type ProfileCard } from "@/lib/socket";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const RECOGNITION_API_KEY = process.env.NEXT_PUBLIC_RECOGNITION_API_KEY?.trim() || null;
const RESULTS_CACHE_KEY = "recognition_results_cache";

type FrameDetectionResponse = {
  matches: ProfileCard[];
  processing_time_ms: number;
  event_id: string | null;
};

function resolvePhotoUrl(photoPath: string | null): string | null {
  if (!photoPath) return null;
  const normalizedPhotoPath = photoPath.trim();
  if (!normalizedPhotoPath) return null;
  return normalizedPhotoPath;
}

interface RecognitionResult {
  id: string;
  user_id: string;
  matched_user_id: string | null;
  confidence: number | null;
  created_at: string;
  profile?: ProfileResponse;
  compatibility?: CompatibilityResponse;
}

function loadCachedResults(): RecognitionResult[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = sessionStorage.getItem(RESULTS_CACHE_KEY);
    if (!raw) return [];
    return JSON.parse(raw) as RecognitionResult[];
  } catch {
    return [];
  }
}

function saveCachedResults(results: RecognitionResult[]) {
  try {
    sessionStorage.setItem(RESULTS_CACHE_KEY, JSON.stringify(results));
  } catch { /* storage full — silently ignore */ }
}


export default function RecognitionPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const selectedEventId = useMemo(() => {
    const eventId = searchParams.get("event_id")?.trim();
    if (eventId) {
      return eventId;
    }
    return process.env.NEXT_PUBLIC_RECOGNITION_EVENT_ID?.trim() ?? null;
  }, [searchParams]);
  const [results, setResults] = useState<RecognitionResult[]>(loadCachedResults);
  const [searchText, setSearchText] = useState("");
  const [sortMode, setSortMode] = useState<"recent" | "compatible">("recent");
  const [loading, setLoading] = useState(true);
  const [capturing, setCapturing] = useState(false);
  const [captureLoading, setCaptureLoading] = useState(false);
  const cameraMode = true;
  const [consentWarning, setConsentWarning] = useState<string | null>(null);
  const [likedUserIds, setLikedUserIds] = useState<Set<string>>(new Set());
  const [likePendingUserIds, setLikePendingUserIds] = useState<Set<string>>(new Set());
  const socketRef = useRef<SocketClient | null>(null);
  const mountIdRef = useRef(`dashboard-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const cameraActiveRef = useRef(false);
  const accessTokenRef = useRef<string | null>(null);
  // Cache compatibility results per user_id so we don't refetch on every frame
  const compatCacheRef = useRef<Map<string, CompatibilityResponse>>(new Map());

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
        if (parsed.matched_user_id) void attachCompatibility(parsed.matched_user_id);
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
        accessTokenRef.current = null;
        setLoading(false);
        return;
      }

      accessTokenRef.current = session.access_token;
      api.setToken(session.access_token);
      try {
        const likes = await api.getMyProfileLikes();
        setLikedUserIds(new Set(likes.map((like) => like.liked_profile_id)));
      } catch (error) {
        console.error("[Recognition] Failed to load likes:", error);
      }
      socket.connect(session.access_token);
      setLoading(false);

      // Fetch compat for any results already in the cache
      for (const result of loadCachedResults()) {
        if (result.matched_user_id && !result.compatibility) {
          void attachCompatibility(result.matched_user_id);
        }
      }
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

  useEffect(() => {
    saveCachedResults(results);
  }, [results]);

  useEffect(() => {
    let cancelled = false;

    async function loadConsentWarning() {
      if (!selectedEventId || !accessTokenRef.current) {
        setConsentWarning(null);
        return;
      }

      let consent: ConsentResponse | null = getCachedEventConsent(selectedEventId);
      if (!consent) {
        try {
          consent = await api.getMyEventConsent(selectedEventId);
          setCachedEventConsent(selectedEventId, consent);
        } catch (error) {
          console.error("[Recognition] Failed to load event consent:", error);
          return;
        }
      }

      if (cancelled) return;
      if (!consent.allow_profile_display || !consent.allow_recognition) {
        setConsentWarning(
          "One or more event consents are off. You will not be able to recognize other attendees.",
        );
      } else {
        setConsentWarning(null);
      }
    }

    if (!loading) {
      void loadConsentWarning();
    }

    return () => {
      cancelled = true;
    };
  }, [loading, selectedEventId]);

  function stopCameraStream() {
    cameraActiveRef.current = false;
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    if (videoRef.current) videoRef.current.srcObject = null;
  }

  // Camera capture loop — runs while cameraActiveRef is true
  async function runCameraCapture() {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas) return;

    while (cameraActiveRef.current) {
      if (video.readyState >= 2 && video.videoWidth > 0) {
        const maxDim = 640;
        const scale = Math.min(1, maxDim / Math.max(video.videoWidth, video.videoHeight));
        canvas.width = Math.round(video.videoWidth * scale);
        canvas.height = Math.round(video.videoHeight * scale);
        const ctx = canvas.getContext("2d");
        if (ctx) {
          ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
          const imageBase64 = canvas.toDataURL("image/jpeg", 0.7).split(",")[1];
          if (imageBase64) {
            try {
              const headers: Record<string, string> = {
                "Content-Type": "application/json",
              };
              if (accessTokenRef.current) {
                headers["Authorization"] = `Bearer ${accessTokenRef.current}`;
              }
              if (RECOGNITION_API_KEY) {
                headers["X-Recognition-Api-Key"] = RECOGNITION_API_KEY;
              }

              const res = await fetch(`${API_URL}/api/v1/recognition/detect`, {
                method: "POST",
                headers,
                body: JSON.stringify({
                  image_base64: imageBase64,
                  event_id: selectedEventId,
                }),
              });
              if (res.ok) {
                const data = (await res.json()) as FrameDetectionResponse;
                for (const match of data.matches) {
                  const result: RecognitionResult = {
                    id: match.user_id,
                    user_id: match.user_id,
                    matched_user_id: match.user_id,
                    confidence: match.face_similarity,
                    created_at: new Date().toISOString(),
                    profile: toProfileResponse(match),
                  };
                  setResults((prev) => upsertRecognitionResult(prev, result));
                  void attachCompatibility(match.user_id);
                }
              } else {
                const errorBody = await res.json().catch(() => null);
                console.error("[Camera] Recognition HTTP error:", {
                  status: res.status,
                  statusText: res.statusText,
                  detail: errorBody,
                  hasAuthorization: Boolean(headers.Authorization),
                  hasRecognitionApiKey: Boolean(headers["X-Recognition-Api-Key"]),
                });
              }
            } catch (err) {
              console.error("[Camera] Recognition error:", err);
            }
          }
        }
      }
      await new Promise<void>((resolve) => setTimeout(resolve, 1500));
    }

    setCapturing(false);
  }

  // Cleanup camera on unmount
  useEffect(() => {
    return () => { stopCameraStream(); };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function attachCompatibility(userId: string) {
    if (compatCacheRef.current.has(userId)) {
      const cached = compatCacheRef.current.get(userId)!;
      setResults((prev) =>
        prev.map((r) => (r.matched_user_id === userId ? { ...r, compatibility: cached } : r))
      );
      return;
    }
    try {
      const compat = await api.getCompatibility(userId);
      compatCacheRef.current.set(userId, compat);
      setResults((prev) =>
        prev.map((r) => (r.matched_user_id === userId ? { ...r, compatibility: compat } : r))
      );
    } catch (err) {
      console.warn("[Compatibility] Failed for", userId, err);
    }
  }

  async function toggleCapture() {
    if (cameraMode) {
      if (capturing) {
        stopCameraStream();
        setCapturing(false);
      } else {
        setCaptureLoading(true);
        try {
          const stream = await navigator.mediaDevices.getUserMedia({
            video: { facingMode: "environment" },
          });
          streamRef.current = stream;
          if (videoRef.current) {
            videoRef.current.srcObject = stream;
            await videoRef.current.play();
          }
          cameraActiveRef.current = true;
          setCapturing(true);
          runCameraCapture().catch((err) => {
            console.error("[Camera] Loop error:", err);
            stopCameraStream();
            setCapturing(false);
          });
        } catch (err) {
          console.error("[Camera] getUserMedia failed:", err);
        }
        setCaptureLoading(false);
      }
      return;
    }

    // Glasses mode
    const socket = socketRef.current;
    if (!socket) return;

    setCaptureLoading(true);
    try {
      if (!socket.isConnected()) socket.connect(accessTokenRef.current ?? undefined);
      const connected = await waitForSocketConnection(socket);
      if (connected) {
        const sent = socket.send(
          capturing
            ? { type: "stop_recognition" }
            : { type: "start_recognition", payload: selectedEventId ? { event_id: selectedEventId } : undefined },
        );
        if (sent && capturing) setCapturing(false);
      }
    } catch { /* ignore */ }
    setCaptureLoading(false);
  }

  async function handleSignOut() {
    await signOutUser();
    router.push("/");
    router.refresh();
  }

  async function toggleLike(userId: string) {
    if (likePendingUserIds.has(userId)) return;
    const currentlyLiked = likedUserIds.has(userId);
    if (!currentlyLiked && !selectedEventId) return;

    setLikePendingUserIds((prev) => {
      const next = new Set(prev);
      next.add(userId);
      return next;
    });

    setLikedUserIds((prev) => {
      const next = new Set(prev);
      if (currentlyLiked) next.delete(userId);
      else next.add(userId);
      return next;
    });

    try {
      if (currentlyLiked) {
        await api.unlikeProfile(userId);
      } else {
        await api.likeProfile(userId, selectedEventId!);
      }
    } catch (error) {
      // 409 means the like already exists; keep liked state.
      if (!(isApiErrorWithStatus(error, 409) && !currentlyLiked)) {
        setLikedUserIds((prev) => {
          const next = new Set(prev);
          if (currentlyLiked) next.add(userId);
          else next.delete(userId);
          return next;
        });
      }
    } finally {
      setLikePendingUserIds((prev) => {
        const next = new Set(prev);
        next.delete(userId);
        return next;
      });
    }
  }

  const filteredAndSortedResults = useMemo(() => {
    const query = searchText.trim().toLowerCase();
    const filtered = query
      ? results.filter((result) => {
          const profile = result.profile;
          const haystack = [
            profile?.full_name ?? "",
            profile?.headline ?? "",
            profile?.company ?? "",
            profile?.major ?? "",
            profile?.location ?? "",
          ]
            .join(" ")
            .toLowerCase();
          return haystack.includes(query);
        })
      : [...results];

    if (sortMode === "compatible") {
      filtered.sort((a, b) => {
        const aScore = a.compatibility?.score ?? -1;
        const bScore = b.compatibility?.score ?? -1;
        if (aScore !== bScore) return bScore - aScore;
        return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
      });
      return filtered;
    }

    filtered.sort(
      (a, b) =>
        new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
    );
    return filtered;
  }, [results, searchText, sortMode]);

  return (
    <div className="relative flex min-h-dvh flex-col overflow-hidden">
      {/* Hidden camera elements for phone camera mode */}
      {/* eslint-disable-next-line jsx-a11y/media-has-caption */}
      <video ref={videoRef} className="hidden" playsInline muted />
      <canvas ref={canvasRef} className="hidden" />

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

          <div className="flex items-center gap-2">
            {/* Mode indicator */}
            <div
              className="flex items-center gap-1.5 rounded-full px-2.5 py-1.5"
              style={{
                background: "oklch(1 0 0 / 5%)",
                border: "1px solid oklch(1 0 0 / 8%)",
              }}
            >
              <ScanFace className="h-3.5 w-3.5" style={{ color: "oklch(1 0 0 / 30%)" }} />
              <span
                className="text-[10px] font-medium uppercase tracking-[0.1em]"
                style={{ color: "oklch(1 0 0 / 25%)" }}
              >
                Glasses
              </span>
            </div>

            {/* Scan / Stop button */}
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
      </div>

      {/* Content */}
      <div className="relative z-10 flex-1 overflow-y-auto px-6 pb-4">
        {consentWarning ? (
          <div
            className="mb-3 rounded-2xl px-3 py-2 text-[12px] text-amber-200/90"
            style={{
              background: "oklch(0.3 0.09 70 / 22%)",
              border: "1px solid oklch(0.72 0.14 70 / 38%)",
            }}
          >
            {consentWarning}
          </div>
        ) : null}
        {loading ? (
          <div className="flex items-center justify-center py-16">
            <div className="h-6 w-6 animate-spin rounded-full border-2 border-white/10 border-t-white/40" />
          </div>
        ) : results.length === 0 ? (
          <EmptyState />
        ) : (
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <input
                type="text"
                value={searchText}
                onChange={(event) => setSearchText(event.target.value)}
                placeholder="Search recognized profiles..."
                className="h-9 w-full rounded-full border border-white/10 bg-white/[0.04] px-3 text-[13px] text-white placeholder:text-white/30 outline-none"
              />
              <button
                type="button"
                onClick={() => setSortMode((prev) => (prev === "recent" ? "compatible" : "recent"))}
                className="h-9 shrink-0 rounded-full border border-white/10 bg-white/[0.04] px-3 text-[11px] font-medium uppercase tracking-[0.08em] text-white/70 transition-colors hover:text-white"
                title="Toggle sort mode"
              >
                {sortMode === "recent" ? "Recent" : "Compatible"}
              </button>
            </div>

            {filteredAndSortedResults.length === 0 ? (
              <div className="rounded-xl border border-white/10 bg-white/[0.03] px-4 py-6 text-center text-[13px] text-white/40">
                No recognized profiles match your search.
              </div>
            ) : filteredAndSortedResults.map((result, i) => (
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
                  const params = new URLSearchParams();
                  if (selectedEventId) {
                    params.set("event_id", selectedEventId);
                  }
                  if (r.confidence != null) {
                    params.set("accuracy", String(Math.round(r.confidence)));
                  }
                  const qs = params.toString();
                  router.push(`/profile/${userId}${qs ? `?${qs}` : ""}`);
                }}
                liked={Boolean(result.matched_user_id && likedUserIds.has(result.matched_user_id))}
                likePending={Boolean(
                  result.matched_user_id && likePendingUserIds.has(result.matched_user_id),
                )}
                canLike={Boolean(result.matched_user_id && selectedEventId)}
                onToggleLike={(targetUserId) => {
                  void toggleLike(targetUserId);
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
  liked,
  likePending,
  canLike,
  onToggleLike,
}: {
  result: RecognitionResult;
  index: number;
  onSelect: (result: RecognitionResult) => void;
  liked: boolean;
  likePending: boolean;
  canLike: boolean;
  onToggleLike: (userId: string) => void;
}) {
  const [imgFailed, setImgFailed] = useState(false);
  const profile = result.profile;
  const compat = result.compatibility;
  const name = profile?.full_name ?? "Unknown person";
  const initials = name.split(" ").map((n) => n[0]).join("").slice(0, 2).toUpperCase();
  const photoUrl = resolvePhotoUrl(profile?.photo_path ?? null);
  const confidencePct = result.confidence != null ? Math.round(result.confidence) : null;

  const sharedThings = [
  ...(compat?.shared_companies ?? []),
  ...(compat?.shared_schools ?? []),
  ...(compat?.shared_fields ?? []),
];
const firstStarter =
    compat?.conversation_starters?.[0] ??
    (profile ? `Hi ${profile.full_name ?? name}, great to meet you — what brings you to this event?` : undefined);

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
                <div className="flex items-center gap-1.5 shrink-0">
                  {compat ? (
                    <span
                      className="rounded-full px-2 py-0.5 text-[10px] font-medium"
                      style={{
                        background: "oklch(0.30 0.12 145 / 40%)",
                        border: "1px solid oklch(0.5 0.15 145 / 30%)",
                        color: "oklch(0.78 0.14 145)",
                      }}
                    >
                      {Math.round(compat.score)}% match
                    </span>
                  ) : (
                    <span
                      className="rounded-full px-2 py-0.5 text-[10px] font-medium"
                      style={{
                        background: "oklch(0.30 0.12 145 / 40%)",
                        border: "1px solid oklch(0.5 0.15 145 / 30%)",
                        color: "oklch(0.78 0.14 145 / 40%)",
                      }}
                    >
                      …% match
                    </span>
                  )}
                </div>
              </div>
              {sharedThings.length > 0 && (
                <p className="text-[11px] mt-1.5 leading-snug" style={{ color: "oklch(0.7 0.12 145)" }}>
                  Also: {sharedThings.slice(0, 2).join(" · ")}
                </p>
              )}
              {firstStarter && (
                <p className="text-[11px] text-white/30 mt-1.5 leading-snug line-clamp-2 italic">
                  &ldquo;{firstStarter}&rdquo;
                </p>
              )}
              {!sharedThings.length && !firstStarter && profile?.profile_one_liner && (
                <p className="truncate text-[13px] text-white/50 mt-0.5">{profile.headline}</p>
              )}
              {profile?.profile_one_liner && (
                <p className="text-[12px] text-white/35 mt-1.5 leading-snug line-clamp-2">
                  {profile.profile_one_liner}
                </p>
              )}
            </div>
            <div className="shrink-0 flex items-center gap-2 pt-0.5">
              {result.matched_user_id ? (
                <button
                  type="button"
                  onClick={(event) => {
                    event.stopPropagation();
                    onToggleLike(result.matched_user_id!);
                  }}
                  disabled={likePending || (!liked && !canLike)}
                  className="group rounded-full p-1.5 transition-all active:scale-90 disabled:opacity-40"
                  title={!liked && !canLike ? "Event context required to like" : "Toggle like"}
                  aria-label={liked ? "Unlike profile" : "Like profile"}
                >
                  <Heart
                    className={`h-4 w-4 transition-all ${
                      liked ? "fill-red-500 text-red-500 scale-110" : "text-white/40 group-hover:text-white/60"
                    }`}
                  />
                </button>
              ) : null}
              <p className="text-[11px] text-white/22">{formatTime(result.created_at)}</p>
            </div>
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
