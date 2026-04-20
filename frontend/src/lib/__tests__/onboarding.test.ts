import { describe, it, expect, beforeEach } from "vitest";
import {
  saveMissingSteps,
  getFirstMissingRoute,
  getNextRoute,
} from "../onboarding";

describe("onboarding helpers", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  describe("getFirstMissingRoute", () => {
    it("returns /dashboard when no fields are missing", () => {
      expect(getFirstMissingRoute([])).toBe("/dashboard");
    });

    it("returns the route for the first missing field in step order", () => {
      expect(getFirstMissingRoute(["bio", "name"])).toBe("/onboarding/name");
    });

    it("returns /onboarding/photo for profile_pic", () => {
      expect(getFirstMissingRoute(["profile_pic"])).toBe("/onboarding/photo");
    });

    it("returns /onboarding/experience for experiences", () => {
      expect(getFirstMissingRoute(["experiences"])).toBe(
        "/onboarding/experience"
      );
    });

    it("returns /onboarding/education for education", () => {
      expect(getFirstMissingRoute(["education"])).toBe(
        "/onboarding/education"
      );
    });

    it("returns /onboarding/location for location", () => {
      expect(getFirstMissingRoute(["location"])).toBe("/onboarding/location");
    });

    it("returns /onboarding/bio for bio", () => {
      expect(getFirstMissingRoute(["bio"])).toBe("/onboarding/bio");
    });

    it("respects step order: name before photo before location", () => {
      expect(getFirstMissingRoute(["location", "profile_pic", "name"])).toBe(
        "/onboarding/name"
      );
    });

    it("ignores unknown backend fields", () => {
      expect(getFirstMissingRoute(["unknown_field"])).toBe("/dashboard");
    });

    it("skips unknown fields and returns first known", () => {
      expect(getFirstMissingRoute(["unknown", "bio"])).toBe("/onboarding/bio");
    });
  });

  describe("saveMissingSteps", () => {
    it("persists steps to localStorage", () => {
      saveMissingSteps(["name", "bio"]);
      const stored = JSON.parse(localStorage.getItem("onboarding_missing_steps")!);
      expect(stored).toEqual(["name", "bio"]);
    });

    it("filters out unknown fields", () => {
      saveMissingSteps(["name", "unknown_field", "bio"]);
      const stored = JSON.parse(localStorage.getItem("onboarding_missing_steps")!);
      expect(stored).toEqual(["name", "bio"]);
    });

    it("maps backend field names to step names", () => {
      saveMissingSteps(["profile_pic", "experiences"]);
      const stored = JSON.parse(localStorage.getItem("onboarding_missing_steps")!);
      expect(stored).toEqual(["photo", "experience"]);
    });
  });

  describe("getNextRoute", () => {
    it("returns /dashboard when no steps are saved (all steps fallback) and current is last", () => {
      expect(getNextRoute("education")).toBe("/dashboard");
    });

    it("returns next missing step after current", () => {
      saveMissingSteps(["name", "bio", "education"]);
      expect(getNextRoute("name")).toBe("/onboarding/bio");
    });

    it("returns /dashboard when current step is last missing step", () => {
      saveMissingSteps(["name", "bio"]);
      expect(getNextRoute("bio")).toBe("/dashboard");
    });

    it("skips completed steps", () => {
      saveMissingSteps(["name", "education"]);
      expect(getNextRoute("name")).toBe("/onboarding/education");
    });

    it("returns /dashboard when there are no missing steps", () => {
      saveMissingSteps([]);
      expect(getNextRoute("name")).toBe("/dashboard");
    });

    it("returns first available step after current even if not adjacent", () => {
      saveMissingSteps(["name", "experiences"]);
      expect(getNextRoute("name")).toBe("/onboarding/experience");
    });

    it("falls back to showing all steps when localStorage is empty", () => {
      expect(getNextRoute("name")).toBe("/onboarding/photo");
    });
  });
});
