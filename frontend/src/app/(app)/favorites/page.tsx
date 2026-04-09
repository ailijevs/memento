"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { api, isApiErrorWithStatus, type ProfileLikeResponse, type ProfileResponse } from "@/lib/api";
import { Aurora } from "@/components/aurora";
import { ConfirmationDialog } from "@/components/confirmation-dialog";
import { Heart, Search } from "lucide-react";

type FavoriteItem = {
  like: ProfileLikeResponse;
  profile: ProfileResponse | null;
  liked: boolean;
  pending: boolean;
};

function resolvePhotoUrl(photoPath: string | null): string | null {
  if (!photoPath) return null;
  const normalizedPhotoPath = photoPath.trim();
  if (!normalizedPhotoPath) return null;
  return normalizedPhotoPath;
}

export default function FavoritesPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [favorites, setFavorites] = useState<FavoriteItem[]>([]);
  const [confirmUnlikeUserId, setConfirmUnlikeUserId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");

  useEffect(() => {
    async function load() {
      const supabase = createClient();
      const {
        data: { session },
      } = await supabase.auth.getSession();
      if (!session) {
        router.push("/login");
        return;
      }

      api.setToken(session.access_token);
      try {
        const likes = await api.getMyProfileLikes();
        const profiles = await Promise.all(
          likes.map(async (like) => {
            try {
              return await api.getProfileById(like.liked_profile_id);
            } catch {
              return null;
            }
          }),
        );

        setFavorites(
          likes.map((like, index) => ({
            like,
            profile: profiles[index],
            liked: true,
            pending: false,
          })),
        );
      } finally {
        setLoading(false);
      }
    }

    void load();
  }, [router]);

  async function runLikeToggle(targetUserId: string) {
    const target = favorites.find((item) => item.like.liked_profile_id === targetUserId);
    if (!target || target.pending) return;

    setFavorites((prev) => {
      const next = prev.map((item) => {
        if (item.like.liked_profile_id !== targetUserId) return item;
        return { ...item, pending: true, liked: !item.liked };
      });
      return next;
    });

    try {
      if (target.liked) {
        await api.unlikeProfile(targetUserId);
      } else {
        if (!target.like.event_id) {
          throw new Error("Cannot re-like without event context.");
        }
        await api.likeProfile(targetUserId, target.like.event_id);
      }
    } catch (error) {
      if (!(isApiErrorWithStatus(error, 409) && !target.liked)) {
        setFavorites((prev) =>
          prev.map((item) =>
            item.like.liked_profile_id === targetUserId
              ? { ...item, liked: target!.liked, pending: false }
              : item,
          ),
        );
        return;
      }
    }

    setFavorites((prev) =>
      prev.map((item) =>
        item.like.liked_profile_id === targetUserId ? { ...item, pending: false } : item,
      ),
    );
  }

  async function toggleLike(targetUserId: string) {
    const target = favorites.find((item) => item.like.liked_profile_id === targetUserId);
    if (!target || target.pending) return;

    if (target.liked) {
      setConfirmUnlikeUserId(targetUserId);
      return;
    }

    await runLikeToggle(targetUserId);
  }

  const normalizedQuery = searchQuery.trim().toLowerCase();
  const visibleFavorites = favorites.filter((item) => {
    if (!item.liked) return false;
    if (!normalizedQuery) return true;

    const name = item.profile?.full_name?.toLowerCase() ?? "";
    const headline = item.profile?.headline?.toLowerCase() ?? "";
    const eventName = item.like.event_name?.toLowerCase() ?? "";
    return (
      name.includes(normalizedQuery) ||
      headline.includes(normalizedQuery) ||
      eventName.includes(normalizedQuery)
    );
  });

  return (
    <div className="relative flex min-h-dvh flex-col overflow-hidden">
      <div className="absolute inset-0" style={{ opacity: 0.45 }}>
        <Aurora className="h-full w-full" mode="focused" />
      </div>
      <div
        className="pointer-events-none absolute inset-0"
        style={{
          background: "linear-gradient(to bottom, transparent 20%, oklch(0.07 0.015 270) 55%)",
        }}
      />

      <div className="relative z-10 px-6 pt-14 pb-5">
        <h1
          className="text-white"
          style={{
            fontFamily: "var(--font-serif)",
            fontSize: 28,
            fontWeight: 400,
            letterSpacing: "-0.02em",
          }}
        >
          Favorites
        </h1>
        <div
          className="mt-3 flex items-center gap-2 rounded-2xl px-3 py-2.5"
          style={{
            background: "rgba(255,255,255,0.06)",
            border: "1px solid rgba(255,255,255,0.10)",
          }}
        >
          <Search className="h-4 w-4 text-white/35" />
          <input
            value={searchQuery}
            onChange={(event) => setSearchQuery(event.target.value)}
            placeholder="Search favorites"
            className="w-full bg-transparent text-[14px] text-white placeholder:text-white/30 outline-none"
          />
        </div>
      </div>

      <div className="relative z-10 flex-1 overflow-y-auto px-6 pb-4">
        {loading ? (
          <div className="flex items-center justify-center py-16">
            <div className="h-6 w-6 animate-spin rounded-full border-2 border-white/10 border-t-white/40" />
          </div>
        ) : visibleFavorites.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <p className="text-[15px] text-white/30">
              {normalizedQuery ? "No matches found" : "No favorites yet"}
            </p>
            <p className="mt-2 text-[13px] text-white/15">
              {normalizedQuery
                ? "Try a different name, headline, or event"
                : "Like people from recognition to save them here"}
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {visibleFavorites.map((item, index) => (
              <FavoriteCard
                key={item.like.liked_profile_id}
                item={item}
                index={index}
                onSelect={() => {
                  const profilePath = item.like.event_id
                    ? `/profile/${item.like.liked_profile_id}?event_id=${encodeURIComponent(item.like.event_id)}&source=favorites`
                    : `/profile/${item.like.liked_profile_id}?source=favorites`;
                  router.push(profilePath);
                }}
                onToggleLike={() => {
                  void toggleLike(item.like.liked_profile_id);
                }}
              />
            ))}
          </div>
        )}
      </div>

      <ConfirmationDialog
        open={Boolean(confirmUnlikeUserId)}
        title="Remove Favorite?"
        message="This profile will be removed from your favorites."
        confirmLabel="Remove"
        onConfirm={() => {
          const targetUserId = confirmUnlikeUserId;
          setConfirmUnlikeUserId(null);
          if (!targetUserId) return;
          void runLikeToggle(targetUserId);
        }}
        onCancel={() => setConfirmUnlikeUserId(null)}
      />
    </div>
  );
}

function FavoriteCard({
  item,
  index,
  onSelect,
  onToggleLike,
}: {
  item: FavoriteItem;
  index: number;
  onSelect: () => void;
  onToggleLike: () => void;
}) {
  const [imgFailed, setImgFailed] = useState(false);
  const profile = item.profile;
  const name = profile?.full_name ?? "Unknown person";
  const initials = name
    .split(" ")
    .map((n) => n[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
  const photoUrl = resolvePhotoUrl(profile?.photo_path ?? null);

  return (
    <div
      className="rounded-2xl p-4 cursor-pointer active:scale-[0.98] transition-transform"
      style={{
        background: "rgba(255,255,255,0.07)",
        border: "1px solid rgba(255,255,255,0.12)",
        animation: `fade-in 0.4s cubic-bezier(0.16,1,0.3,1) ${index * 45}ms both`,
      }}
      onClick={onSelect}
    >
      <div className="flex items-start gap-3">
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

        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0">
              <p className="truncate text-[15px] font-semibold text-white">{name}</p>
              {profile?.headline && (
                <p className="truncate text-[13px] text-white/45 mt-0.5">{profile.headline}</p>
              )}
              <p className="text-[11px] mt-1.5 text-white/35">
                Met at: {item.like.event_name ?? "Unknown event"}
              </p>
            </div>

            <button
              type="button"
              onClick={(event) => {
                event.stopPropagation();
                onToggleLike();
              }}
              disabled={item.pending}
              className="rounded-full p-1.5 transition-all active:scale-90 disabled:opacity-40"
              aria-label={item.liked ? "Unlike profile" : "Like profile"}
              title={item.liked ? "Unlike" : "Like"}
            >
              <Heart
                className={`h-4 w-4 transition-all ${
                  item.liked ? "fill-red-500 text-red-500 scale-110" : "text-white/40"
                }`}
              />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
