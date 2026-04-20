import { describe, it, expect, beforeEach } from "vitest";
import { getCachedEventConsent, setCachedEventConsent } from "../consent-cache";
import type { ConsentResponse } from "../api";

const CACHE_KEY = "event_consent_cache_v1";

function makeConsent(overrides: Partial<ConsentResponse> = {}): ConsentResponse {
  return {
    event_id: "evt-1",
    user_id: "user-1",
    allow_profile_display: true,
    allow_recognition: false,
    consented_at: "2026-01-01T00:00:00Z",
    revoked_at: null,
    updated_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

describe("consent-cache", () => {
  beforeEach(() => {
    sessionStorage.clear();
  });

  it("returns null when no cache exists", () => {
    expect(getCachedEventConsent("evt-1")).toBeNull();
  });

  it("stores and retrieves a consent", () => {
    const consent = makeConsent();
    setCachedEventConsent("evt-1", consent);
    const cached = getCachedEventConsent("evt-1");
    expect(cached).toEqual(consent);
  });

  it("returns null for a different event ID", () => {
    setCachedEventConsent("evt-1", makeConsent());
    expect(getCachedEventConsent("evt-2")).toBeNull();
  });

  it("overwrites consent for the same event", () => {
    setCachedEventConsent("evt-1", makeConsent({ allow_recognition: false }));
    setCachedEventConsent("evt-1", makeConsent({ allow_recognition: true }));
    const cached = getCachedEventConsent("evt-1");
    expect(cached?.allow_recognition).toBe(true);
  });

  it("stores multiple events independently", () => {
    const consent1 = makeConsent({ event_id: "evt-1" });
    const consent2 = makeConsent({
      event_id: "evt-2",
      allow_recognition: true,
    });
    setCachedEventConsent("evt-1", consent1);
    setCachedEventConsent("evt-2", consent2);

    expect(getCachedEventConsent("evt-1")).toEqual(consent1);
    expect(getCachedEventConsent("evt-2")).toEqual(consent2);
  });

  it("handles corrupted cache gracefully", () => {
    sessionStorage.setItem(CACHE_KEY, "not-valid-json{{{");
    expect(getCachedEventConsent("evt-1")).toBeNull();
  });

  it("handles empty string in cache gracefully", () => {
    sessionStorage.setItem(CACHE_KEY, "");
    expect(getCachedEventConsent("evt-1")).toBeNull();
  });
});
