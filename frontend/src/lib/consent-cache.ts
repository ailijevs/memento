import type { ConsentResponse } from "@/lib/api";

const CONSENT_CACHE_KEY = "event_consent_cache_v1";

type ConsentCacheMap = Record<string, ConsentResponse>;

function readConsentCache(): ConsentCacheMap {
  if (typeof window === "undefined") return {};
  try {
    const raw = sessionStorage.getItem(CONSENT_CACHE_KEY);
    if (!raw) return {};
    return JSON.parse(raw) as ConsentCacheMap;
  } catch {
    return {};
  }
}

function writeConsentCache(cache: ConsentCacheMap): void {
  if (typeof window === "undefined") return;
  try {
    sessionStorage.setItem(CONSENT_CACHE_KEY, JSON.stringify(cache));
  } catch {
    // Ignore storage failures
  }
}

export function getCachedEventConsent(eventId: string): ConsentResponse | null {
  const cache = readConsentCache();
  return cache[eventId] ?? null;
}

export function setCachedEventConsent(eventId: string, consent: ConsentResponse): void {
  const cache = readConsentCache();
  cache[eventId] = consent;
  writeConsentCache(cache);
}

