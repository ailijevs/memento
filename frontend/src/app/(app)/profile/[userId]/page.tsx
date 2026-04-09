"use client";

import { useEffect, useState } from "react";
import { useRouter, useParams, useSearchParams } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { api, isApiErrorWithStatus, type ProfileResponse } from "@/lib/api";
import { Aurora } from "@/components/aurora";
import { ConfirmationDialog } from "@/components/confirmation-dialog";
import { ChevronLeft, MapPin, Briefcase, GraduationCap, ExternalLink, Heart } from "lucide-react";

function resolvePhotoUrl(photoPath: string | null): string | null {
  if (!photoPath) return null;
  const normalizedPhotoPath = photoPath.trim();
  if (!normalizedPhotoPath) return null;
  return normalizedPhotoPath;
}

export default function UserProfilePage() {
  const router = useRouter();
  const params = useParams();
  const searchParams = useSearchParams();
  const userId = params.userId as string;
  const eventId = searchParams.get("event_id")?.trim() || null;
  const source = searchParams.get("source")?.trim() || null;
  const cameFromFavorites = source === "favorites";
  const [profile, setProfile] = useState<ProfileResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [imgFailed, setImgFailed] = useState(false);
  const [liked, setLiked] = useState(false);
  const [likePending, setLikePending] = useState(false);
  const [confirmUnlikeOpen, setConfirmUnlikeOpen] = useState(false);

  useEffect(() => {
    // Show cached data instantly if available
    const cached = sessionStorage.getItem(`profile_cache_${userId}`);
    if (cached) {
      try {
        setProfile(JSON.parse(cached));
        setLoading(false);
      } catch { /* ignore bad cache */ }
    }

    async function load() {
      const supabase = createClient();
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) { router.push("/login"); return; }
      api.setToken(session.access_token);
      try {
        const [p, likes] = await Promise.all([
          api.getProfileById(userId),
          api.getMyProfileLikes(),
        ]);
        setProfile(p);
        setLiked(likes.some((like) => like.liked_profile_id === userId));
        sessionStorage.setItem(`profile_cache_${userId}`, JSON.stringify(p));
      } catch {
        // If fetch fails and we already have cached data, keep showing it
      } finally {
        setLoading(false);
      }
    }
    void load();
  }, [userId, router]);

  async function runToggleLike() {
    if (likePending) return;
    if (!liked && !eventId) return;

    const wasLiked = liked;
    setLikePending(true);
    setLiked(!wasLiked);

    try {
      if (wasLiked) {
        await api.unlikeProfile(userId);
      } else {
        await api.likeProfile(userId, eventId!);
      }
    } catch (error) {
      if (!(isApiErrorWithStatus(error, 409) && !wasLiked)) {
        setLiked(wasLiked);
      }
    } finally {
      setLikePending(false);
    }
  }

  async function toggleLike() {
    if (liked && cameFromFavorites) {
      setConfirmUnlikeOpen(true);
      return;
    }
    await runToggleLike();
  }

  if (loading) {
    return (
      <div className="flex min-h-dvh items-center justify-center">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-white/10 border-t-white/40" />
      </div>
    );
  }

  if (!profile) {
    return (
      <div className="flex min-h-dvh flex-col items-center justify-center gap-4">
        <p className="text-[15px] text-white/40">Profile not found</p>
        <button onClick={() => router.back()} className="text-[13px] text-white/25 active:text-white/50">
          Go back
        </button>
      </div>
    );
  }

  const initials = profile.full_name
    ?.split(" ")
    .map((n) => n[0])
    .join("")
    .slice(0, 2)
    .toUpperCase() ?? "?";

  const photoUrl = resolvePhotoUrl(profile.photo_path);

  return (
    <div className="relative flex min-h-dvh flex-col overflow-hidden">
      <div className="absolute inset-0" style={{ background: "#0d0d14" }} />
      <div className="absolute inset-0" style={{ opacity: 0.38 }}>
        <Aurora className="h-full w-full" mode="ambient" />
      </div>
      <div
        className="pointer-events-none absolute inset-0"
        style={{
          background: "linear-gradient(to bottom, transparent 0%, oklch(0.07 0.015 270) 35%)",
        }}
      />

      {/* Header actions */}
      <div className="relative z-10 px-4 pt-14">
        <div className="flex items-center justify-between">
          <button
            onClick={() => router.back()}
            className="flex items-center gap-1 text-white/40 active:text-white/70 transition-colors"
          >
            <ChevronLeft className="h-5 w-5" />
            <span className="text-[14px]">Back</span>
          </button>
          <button
            type="button"
            onClick={() => {
              void toggleLike();
            }}
            disabled={likePending || (!liked && !eventId)}
            className="rounded-full p-2 transition-all active:scale-90 disabled:opacity-40"
            title={!liked && !eventId ? "Event context required to like" : "Toggle like"}
            aria-label={liked ? "Unlike profile" : "Like profile"}
          >
            <Heart
              className={`h-5 w-5 transition-all ${
                liked ? "fill-red-500 text-red-500 scale-110" : "text-white/45"
              }`}
            />
          </button>
        </div>
      </div>

      {/* Scrollable content */}
      <div className="relative z-10 flex-1 overflow-y-auto px-6 pt-6 pb-10">
        {/* Avatar + name */}
        <div className="mb-8 flex flex-col items-center">
          {photoUrl && !imgFailed ? (
            <img
              src={photoUrl}
              alt={profile.full_name}
              className="mb-4 h-20 w-20 rounded-full object-cover"
              style={{ border: "1.5px solid rgba(255,255,255,0.15)" }}
              onError={() => setImgFailed(true)}
            />
          ) : (
            <div
              className="mb-4 flex h-20 w-20 items-center justify-center rounded-full text-[22px] font-light text-white/60"
              style={{
                background: "rgba(255,255,255,0.06)",
                border: "1.5px solid rgba(255,255,255,0.12)",
              }}
            >
              {initials}
            </div>
          )}

          <p
            className="text-white"
            style={{
              fontFamily: "var(--font-serif)",
              fontSize: 28,
              fontWeight: 400,
              letterSpacing: "-0.02em",
            }}
          >
            {profile.full_name}
          </p>

          {profile.headline && (
            <p className="mt-1 text-center text-[15px] text-white/50">{profile.headline}</p>
          )}

          {profile.linkedin_url && (
            <a
              href={profile.linkedin_url}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-3 flex items-center gap-1.5 text-[12px] text-white/30 active:text-white/60"
            >
              <ExternalLink className="h-3 w-3" />
              LinkedIn
            </a>
          )}
        </div>

        <div className="space-y-3">
          {/* Summary */}
          {profile.profile_summary && (
            <SectionCard label="Summary" icon={null}>
              <p className="text-[14px] leading-relaxed text-white/60">{profile.profile_summary}</p>
            </SectionCard>
          )}

          {/* About */}
          {profile.bio && (
            <SectionCard label="About" icon={null}>
              <p className="text-[14px] leading-relaxed text-white/60">{profile.bio}</p>
            </SectionCard>
          )}

          {/* Location */}
          {profile.location && (
            <SectionCard label="Location" icon={<MapPin className="h-3.5 w-3.5" />}>
              <p className="text-[14px] text-white/60">{profile.location}</p>
            </SectionCard>
          )}

          {/* Work */}
          {(profile.company || (profile.experiences && profile.experiences.length > 0)) && (
            <SectionCard label="Work" icon={<Briefcase className="h-3.5 w-3.5" />}>
              {profile.company && (
                <p className="text-[14px] text-white/60">{profile.company}</p>
              )}
              {profile.experiences && profile.experiences.length > 0 && (
                <div className="mt-3 space-y-2.5 border-t border-white/[0.06] pt-3">
                  {profile.experiences.slice(0, 3).map((exp, i) => (
                    <div key={i}>
                      <p className="text-[13px] font-medium text-white/70">{exp.title}</p>
                      <p className="text-[12px] text-white/40">
                        {exp.company}
                        {exp.start_date &&
                          ` · ${exp.start_date}${exp.end_date ? ` – ${exp.end_date}` : " – Present"}`}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </SectionCard>
          )}

          {/* Education */}
          {(profile.major || (profile.education && profile.education.length > 0)) && (
            <SectionCard label="Education" icon={<GraduationCap className="h-3.5 w-3.5" />}>
              {profile.major && (
                <p className="text-[14px] text-white/60">{profile.major}</p>
              )}
              {profile.education && profile.education.length > 0 && (
                <div className="mt-3 space-y-2.5 border-t border-white/[0.06] pt-3">
                  {profile.education.slice(0, 2).map((edu, i) => (
                    <div key={i}>
                      <p className="text-[13px] font-medium text-white/70">{edu.school}</p>
                      <p className="text-[12px] text-white/40">
                        {[edu.degree, edu.field_of_study].filter(Boolean).join(", ")}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </SectionCard>
          )}
        </div>
      </div>

      <ConfirmationDialog
        open={confirmUnlikeOpen}
        title="Remove Favorite?"
        message="This profile will be removed from your favorites."
        confirmLabel="Remove"
        onConfirm={() => {
          setConfirmUnlikeOpen(false);
          void runToggleLike();
        }}
        onCancel={() => setConfirmUnlikeOpen(false)}
      />
    </div>
  );
}

function SectionCard({
  label,
  icon,
  children,
}: {
  label: string;
  icon: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div
      className="rounded-2xl px-4 py-4"
      style={{
        background: "rgba(255,255,255,0.07)",
        border: "1px solid rgba(255,255,255,0.12)",
      }}
    >
      <div className="mb-2.5 flex items-center gap-1.5 text-white/35">
        {icon}
        <span className="text-[10px] font-semibold uppercase tracking-[0.14em]">{label}</span>
      </div>
      {children}
    </div>
  );
}
