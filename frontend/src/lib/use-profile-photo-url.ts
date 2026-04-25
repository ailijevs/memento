import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";

const REFRESH_BUFFER_MS = 30_000;
const CACHE_KEY = "profile_photo_url_cache";

type CachedPhotoUrl = {
  photoPath: string;
  photoUrl: string;
  expiresAt: string;
};

function loadCachedPhotoUrl(photoPath: string): CachedPhotoUrl | null {
  if (typeof window === "undefined") return null;
  const raw = window.sessionStorage.getItem(CACHE_KEY);
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as CachedPhotoUrl;
    if (parsed.photoPath !== photoPath) return null;
    if (!parsed.photoUrl || !parsed.expiresAt) return null;
    const expiryMs = new Date(parsed.expiresAt).getTime();
    if (!Number.isFinite(expiryMs)) return null;
    if (expiryMs - Date.now() <= REFRESH_BUFFER_MS) return null;
    return parsed;
  } catch {
    return null;
  }
}

function saveCachedPhotoUrl(value: CachedPhotoUrl): void {
  if (typeof window === "undefined") return;
  window.sessionStorage.setItem(CACHE_KEY, JSON.stringify(value));
}

function clearCachedPhotoUrl(): void {
  if (typeof window === "undefined") return;
  window.sessionStorage.removeItem(CACHE_KEY);
}

export function useProfilePhotoUrl(photoPath: string | null | undefined) {
  const [photoUrl, setPhotoUrl] = useState<string | null>(null);
  const [expiresAt, setExpiresAt] = useState<string | null>(null);
  const refreshTimerRef = useRef<number | null>(null);
  const retriedUrlRef = useRef<string | null>(null);

  const clearRefreshTimer = useCallback(() => {
    if (refreshTimerRef.current !== null) {
      window.clearTimeout(refreshTimerRef.current);
      refreshTimerRef.current = null;
    }
  }, []);

  const refreshPhotoUrl = useCallback(async () => {
    // `undefined` means profile data has not loaded yet; do nothing.
    if (photoPath === undefined) {
      return;
    }

    const normalized = (photoPath ?? "").trim();
    if (!normalized) {
      setPhotoUrl(null);
      setExpiresAt(null);
      retriedUrlRef.current = null;
      clearRefreshTimer();
      clearCachedPhotoUrl();
      return;
    }

    const cached = loadCachedPhotoUrl(normalized);
    if (cached) {
      setPhotoUrl(cached.photoUrl);
      setExpiresAt(cached.expiresAt);
      return;
    }

    try {
      const response = await api.getMyProfilePhotoUrl();
      const nextPhotoUrl = response.photo_url ?? null;
      const nextExpiresAt = response.expires_at ?? null;
      setPhotoUrl(nextPhotoUrl);
      setExpiresAt(nextExpiresAt);
      if (nextPhotoUrl && nextExpiresAt) {
        saveCachedPhotoUrl({
          photoPath: normalized,
          photoUrl: nextPhotoUrl,
          expiresAt: nextExpiresAt,
        });
      } else {
        clearCachedPhotoUrl();
      }
      retriedUrlRef.current = null;
    } catch {
      setPhotoUrl(null);
      setExpiresAt(null);
      clearRefreshTimer();
    }
  }, [photoPath, clearRefreshTimer]);

  const handleImageError = useCallback(() => {
    if (!photoUrl) return;
    if (retriedUrlRef.current === photoUrl) return;
    retriedUrlRef.current = photoUrl;
    void refreshPhotoUrl();
  }, [photoUrl, refreshPhotoUrl]);

  useEffect(() => {
    void refreshPhotoUrl();
    return clearRefreshTimer;
  }, [refreshPhotoUrl, clearRefreshTimer]);

  useEffect(() => {
    clearRefreshTimer();
    if (!expiresAt) return;

    const expiryMs = new Date(expiresAt).getTime();
    if (!Number.isFinite(expiryMs)) return;

    const delayMs = Math.max(expiryMs - Date.now() - REFRESH_BUFFER_MS, 1_000);
    refreshTimerRef.current = window.setTimeout(() => {
      void refreshPhotoUrl();
    }, delayMs);

    return clearRefreshTimer;
  }, [expiresAt, refreshPhotoUrl, clearRefreshTimer]);

  return {
    photoUrl,
    refreshPhotoUrl,
    handleImageError,
  };
}
