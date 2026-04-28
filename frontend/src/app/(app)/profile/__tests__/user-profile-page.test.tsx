import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  mockPush,
  mockBack,
  mockParams,
  resetNavigationMocks,
} from "@/test/mocks/next-navigation";
import {
  mockGetSession,
  resetSupabaseMocks,
  mockSessionWith,
  mockNoSession,
} from "@/test/mocks/supabase";

const mockGetProfileById = vi.fn();

vi.mock("@/lib/api", () => ({
  api: {
    setToken: vi.fn(),
    getProfileById: (...args: unknown[]) => mockGetProfileById(...args),
    getMyProfileLikes: vi.fn().mockResolvedValue([]),
  },
  isApiErrorWithStatus: () => false,
}));

vi.mock("@/components/aurora", () => ({
  Aurora: () => <div data-testid="aurora" />,
}));

const MOCK_PROFILE = {
  user_id: "user-123",
  full_name: "Akash Kumar",
  headline: "Software Engineer at Google",
  bio: "Building cool stuff",
  location: "San Francisco, CA",
  company: "Google",
  major: "Computer Science",
  graduation_year: 2024,
  linkedin_url: "https://linkedin.com/in/akash",
  photo_path: "https://example.com/photo.jpg",
  experiences: [
    {
      company: "Google",
      title: "Software Engineer",
      start_date: "2024-06",
      end_date: null,
      description: null,
      location: "SF",
    },
  ],
  education: [
    {
      school: "Purdue University",
      degree: "BS",
      field_of_study: "Computer Science",
      start_date: "2020-08",
      end_date: "2024-05",
    },
  ],
  profile_one_liner: null,
  profile_summary: "Experienced software engineer",
};

import UserProfilePage from "../[userId]/page";

describe("UserProfilePage", () => {
  beforeEach(() => {
    resetNavigationMocks();
    resetSupabaseMocks();
    mockGetProfileById.mockClear();
    mockParams.mockReturnValue({ userId: "user-123" });
    sessionStorage.clear();
  });

  it("redirects to login when no session", async () => {
    mockNoSession();
    mockGetProfileById.mockRejectedValue(new Error("no auth"));

    render(<UserProfilePage />);

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith("/login");
    });
  });

  it("renders profile data after loading", async () => {
    mockSessionWith();
    mockGetProfileById.mockResolvedValue(MOCK_PROFILE);

    render(<UserProfilePage />);

    await waitFor(() => {
      expect(screen.getByText("Akash Kumar")).toBeInTheDocument();
    });

    expect(screen.getByText("Software Engineer at Google")).toBeInTheDocument();
    expect(screen.getByText("San Francisco, CA")).toBeInTheDocument();
    expect(screen.getByText("Building cool stuff")).toBeInTheDocument();
  });

  it("renders experience section", async () => {
    mockSessionWith();
    mockGetProfileById.mockResolvedValue(MOCK_PROFILE);

    render(<UserProfilePage />);

    await waitFor(() => {
      expect(screen.getByText("Software Engineer")).toBeInTheDocument();
    });
  });

  it("renders education section", async () => {
    mockSessionWith();
    mockGetProfileById.mockResolvedValue(MOCK_PROFILE);

    render(<UserProfilePage />);

    await waitFor(() => {
      expect(screen.getByText("Purdue University")).toBeInTheDocument();
    });
    expect(screen.getByText("BS, Computer Science")).toBeInTheDocument();
  });

  it("renders LinkedIn link", async () => {
    mockSessionWith();
    mockGetProfileById.mockResolvedValue(MOCK_PROFILE);

    render(<UserProfilePage />);

    await waitFor(() => {
      expect(screen.getByText("LinkedIn")).toBeInTheDocument();
    });
    const link = screen.getByText("LinkedIn").closest("a");
    expect(link).toHaveAttribute("href", "https://linkedin.com/in/akash");
    expect(link).toHaveAttribute("target", "_blank");
  });

  it("renders profile summary section when present", async () => {
    mockSessionWith();
    mockGetProfileById.mockResolvedValue(MOCK_PROFILE);

    render(<UserProfilePage />);

    await waitFor(() => {
      expect(screen.getByText("Experienced software engineer")).toBeInTheDocument();
    });
  });

  it("navigates back when back button is clicked", async () => {
    mockSessionWith();
    mockGetProfileById.mockResolvedValue(MOCK_PROFILE);

    render(<UserProfilePage />);

    await waitFor(() => {
      expect(screen.getByText("Back")).toBeInTheDocument();
    });

    await userEvent.click(screen.getByText("Back"));
    expect(mockBack).toHaveBeenCalled();
  });

  it("shows initials when no photo", async () => {
    mockSessionWith();
    mockGetProfileById.mockResolvedValue({
      ...MOCK_PROFILE,
      photo_path: null,
    });

    render(<UserProfilePage />);

    await waitFor(() => {
      expect(screen.getByText("AK")).toBeInTheDocument();
    });
  });

  it("shows profile not found when API returns null", async () => {
    mockSessionWith();
    mockGetProfileById.mockRejectedValue(new Error("Not found"));

    render(<UserProfilePage />);

    await waitFor(() => {
      expect(screen.getByText("Profile not found")).toBeInTheDocument();
    });
  });

  it("reads cached profile from sessionStorage", () => {
    const cached = { ...MOCK_PROFILE, full_name: "Cached Name" };
    sessionStorage.setItem("profile_cache_user-123", JSON.stringify(cached));

    const stored = sessionStorage.getItem("profile_cache_user-123");
    expect(stored).not.toBeNull();
    const parsed = JSON.parse(stored!);
    expect(parsed.full_name).toBe("Cached Name");
  });

  it("hides optional sections when data is absent", async () => {
    mockSessionWith();
    mockGetProfileById.mockResolvedValue({
      ...MOCK_PROFILE,
      bio: null,
      location: null,
      company: null,
      major: null,
      experiences: null,
      education: null,
      linkedin_url: null,
      profile_summary: null,
    });

    render(<UserProfilePage />);

    await waitFor(() => {
      expect(screen.getByText("Akash Kumar")).toBeInTheDocument();
    });

    expect(screen.queryByText("About")).not.toBeInTheDocument();
    expect(screen.queryByText("Location")).not.toBeInTheDocument();
    expect(screen.queryByText("LinkedIn")).not.toBeInTheDocument();
    expect(screen.queryByText("Summary")).not.toBeInTheDocument();
  });
});
