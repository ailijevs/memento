/**
 * Onboarding step routing helpers.
 * After LinkedIn/resume import, only steps with missing fields are shown.
 */

const STEP_ORDER = ["name", "photo", "location", "bio", "experience", "education"] as const;
export type OnboardingStep = typeof STEP_ORDER[number];

const BACKEND_FIELD_MAP: Record<string, OnboardingStep> = {
  name: "name",
  profile_pic: "photo",
  location: "location",
  bio: "bio",
  experiences: "experience",
  education: "education",
};

const STEP_ROUTES: Record<OnboardingStep, string> = {
  name: "/onboarding/name",
  photo: "/onboarding/photo",
  location: "/onboarding/location",
  bio: "/onboarding/bio",
  experience: "/onboarding/experience",
  education: "/onboarding/education",
};

const STORAGE_KEY = "onboarding_missing_steps";

/** Called after import — persists which steps need to be completed. */
export function saveMissingSteps(backendMissingFields: string[]) {
  const steps = backendMissingFields
    .map((f) => BACKEND_FIELD_MAP[f])
    .filter(Boolean) as OnboardingStep[];
  if (typeof localStorage !== "undefined") {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(steps));
  }
}

/** Returns the route for the first missing step, or /onboarding/enroll if none. */
export function getFirstMissingRoute(backendMissingFields: string[]): string {
  const steps = backendMissingFields
    .map((f) => BACKEND_FIELD_MAP[f])
    .filter(Boolean) as OnboardingStep[];
  const first = STEP_ORDER.find((s) => steps.includes(s));
  return first ? STEP_ROUTES[first] : "/onboarding/enroll";
}

/** Returns the next route after `currentStep` that is still missing, or /onboarding/enroll. */
export function getNextRoute(currentStep: OnboardingStep): string {
  let missingSteps: OnboardingStep[] = [...STEP_ORDER]; // fallback: show all
  if (typeof localStorage !== "undefined") {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) missingSteps = JSON.parse(raw) as OnboardingStep[];
  }
  const currentIdx = STEP_ORDER.indexOf(currentStep);
  const next = STEP_ORDER.slice(currentIdx + 1).find((s) => missingSteps.includes(s));
  return next ? STEP_ROUTES[next] : "/onboarding/enroll";
}
