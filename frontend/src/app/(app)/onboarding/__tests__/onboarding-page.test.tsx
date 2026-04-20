import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  mockBack,
  mockReplace,
  mockPush,
  resetNavigationMocks,
} from "@/test/mocks/next-navigation";
import {
  resetSupabaseMocks,
  mockSessionWith,
} from "@/test/mocks/supabase";

const mockGetProfile = vi.fn();
const mockOnboardFromLinkedIn = vi.fn();
const mockUploadResume = vi.fn();
const mockGetProfileCompletion = vi.fn();

vi.mock("@/lib/api", () => ({
  api: {
    setToken: vi.fn(),
    getProfile: (...args: unknown[]) => mockGetProfile(...args),
    onboardFromLinkedIn: (...args: unknown[]) => mockOnboardFromLinkedIn(...args),
    uploadResume: (...args: unknown[]) => mockUploadResume(...args),
    getProfileCompletion: (...args: unknown[]) => mockGetProfileCompletion(...args),
    updateProfile: vi.fn().mockResolvedValue({}),
  },
}));

vi.mock("@/components/aurora", () => ({
  Aurora: () => <div data-testid="aurora" />,
}));

import OnboardingPage from "../page";

describe("OnboardingPage", () => {
  beforeEach(() => {
    resetNavigationMocks();
    resetSupabaseMocks();
    mockGetProfile.mockClear();
    mockOnboardFromLinkedIn.mockClear();
    mockUploadResume.mockClear();
    mockGetProfileCompletion.mockClear();
  });

  it("renders the build your profile heading", async () => {
    mockSessionWith();
    mockGetProfile.mockRejectedValue(new Error("no profile"));

    render(<OnboardingPage />);

    expect(screen.getByText("Build your profile")).toBeInTheDocument();
  });

  it("renders LinkedIn URL and Resume source options", async () => {
    mockSessionWith();
    mockGetProfile.mockRejectedValue(new Error("no profile"));

    render(<OnboardingPage />);

    expect(screen.getAllByText("LinkedIn URL").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Resume").length).toBeGreaterThanOrEqual(1);
  });

  it("shows step indicator", async () => {
    mockSessionWith();
    mockGetProfile.mockRejectedValue(new Error("no profile"));

    render(<OnboardingPage />);

    expect(screen.getByText("Step 1 of 8")).toBeInTheDocument();
  });

  it("shows description text", async () => {
    mockSessionWith();
    mockGetProfile.mockRejectedValue(new Error("no profile"));

    const { container } = render(<OnboardingPage />);

    expect(container.textContent).toContain("pull in your name, photo, and work history");
  });

  it("shows Import Profile button when LinkedIn URL has value", async () => {
    mockSessionWith();
    mockGetProfile.mockRejectedValue(new Error("no profile"));

    render(<OnboardingPage />);

    const input = screen.getByPlaceholderText("yourname");
    await userEvent.type(input, "johndoe");

    expect(screen.getByText("Import Profile")).toBeInTheDocument();
  });

  it("redirects to dashboard if profile already exists", async () => {
    mockSessionWith();
    mockGetProfile.mockResolvedValue({ user_id: "u1", full_name: "Test" });

    render(<OnboardingPage />);

    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith("/dashboard");
    });
  });

  it("shows error for invalid LinkedIn username", async () => {
    mockSessionWith();
    mockGetProfile.mockRejectedValue(new Error("no profile"));

    render(<OnboardingPage />);

    const input = screen.getByPlaceholderText("yourname");
    await userEvent.type(input, "a");

    await userEvent.click(screen.getByText("Import Profile"));

    await waitFor(() => {
      expect(
        screen.getByText(
          "Please enter a valid LinkedIn username (letters, numbers, and hyphens only)."
        )
      ).toBeInTheDocument();
    });
  });

  it("submits LinkedIn URL and shows preview", async () => {
    mockSessionWith();
    mockGetProfile.mockRejectedValue(new Error("no profile"));
    mockOnboardFromLinkedIn.mockResolvedValue({
      profile: {
        user_id: "u1",
        full_name: "John Doe",
        headline: "Engineer",
        bio: null,
        location: null,
        company: null,
        major: null,
        graduation_year: null,
        linkedin_url: "https://linkedin.com/in/johndoe",
        photo_path: null,
        experiences: [],
        education: [],
        profile_one_liner: null,
        profile_summary: null,
      },
      completion: {
        is_complete: false,
        completion_score: 40,
        missing_fields: ["bio", "location", "profile_pic"],
      },
      enrichment: {},
      image_saved: false,
    });

    render(<OnboardingPage />);

    const input = screen.getByPlaceholderText("yourname");
    await userEvent.type(input, "johndoe");

    await userEvent.click(screen.getByText("Import Profile"));

    await waitFor(() => {
      expect(screen.getByText("Confirm your info")).toBeInTheDocument();
    });

    expect(screen.getByText("John Doe")).toBeInTheDocument();
  });

  it("shows error when LinkedIn import fails", async () => {
    mockSessionWith();
    mockGetProfile.mockRejectedValue(new Error("no profile"));
    mockOnboardFromLinkedIn.mockRejectedValue(new Error("Profile not found"));

    render(<OnboardingPage />);

    const input = screen.getByPlaceholderText("yourname");
    await userEvent.type(input, "validuser");

    await userEvent.click(screen.getByText("Import Profile"));

    await waitFor(() => {
      expect(screen.getByText("Profile not found")).toBeInTheDocument();
    });
  });

  it("has a back button", async () => {
    mockSessionWith();
    mockGetProfile.mockRejectedValue(new Error("no profile"));

    render(<OnboardingPage />);

    const backBtns = document.querySelectorAll(".lucide-chevron-left");
    expect(backBtns.length).toBeGreaterThan(0);
  });
});
