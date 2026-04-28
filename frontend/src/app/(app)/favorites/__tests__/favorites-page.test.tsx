import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  mockPush,
  resetNavigationMocks,
} from "@/test/mocks/next-navigation";
import {
  resetSupabaseMocks,
  mockSessionWith,
  mockNoSession,
} from "@/test/mocks/supabase";

const mockGetMyProfileLikes = vi.fn();
const mockUnlikeProfile = vi.fn();
const mockLikeProfile = vi.fn();

vi.mock("@/lib/api", () => ({
  api: {
    setToken: vi.fn(),
    getMyProfileLikes: (...args: unknown[]) => mockGetMyProfileLikes(...args),
    unlikeProfile: (...args: unknown[]) => mockUnlikeProfile(...args),
    likeProfile: (...args: unknown[]) => mockLikeProfile(...args),
  },
  isApiErrorWithStatus: () => false,
}));

vi.mock("@/components/aurora", () => ({
  Aurora: () => <div data-testid="aurora" />,
}));

import FavoritesPage from "../page";

const MOCK_LIKES = [
  {
    user_id: "viewer-1",
    liked_profile_id: "liked-1",
    event_id: "evt-1",
    event_name: "AI Mixer",
    liked_profile: {
      user_id: "liked-1",
      full_name: "Sarah Chen",
      headline: "ML Engineer",
      bio: null,
      location: null,
      company: null,
      major: null,
      graduation_year: null,
      linkedin_url: null,
      photo_path: null,
      experiences: [],
      education: [],
      profile_one_liner: null,
      profile_summary: null,
    },
    created_at: new Date().toISOString(),
  },
  {
    user_id: "viewer-1",
    liked_profile_id: "liked-2",
    event_id: null,
    event_name: null,
    liked_profile: {
      user_id: "liked-2",
      full_name: "Alex Patel",
      headline: "Product Designer",
      bio: null,
      location: null,
      company: null,
      major: null,
      graduation_year: null,
      linkedin_url: null,
      photo_path: null,
      experiences: [],
      education: [],
      profile_one_liner: null,
      profile_summary: null,
    },
    created_at: new Date().toISOString(),
  },
];

describe("FavoritesPage", () => {
  beforeEach(() => {
    resetNavigationMocks();
    resetSupabaseMocks();
    mockGetMyProfileLikes.mockReset();
    mockUnlikeProfile.mockReset();
    mockLikeProfile.mockReset();
    mockSessionWith();
  });

  it("redirects to login when no session", async () => {
    mockNoSession();
    mockGetMyProfileLikes.mockResolvedValue([]);

    render(<FavoritesPage />);

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith("/login");
    });
  });

  it("renders favorite cards from /me/likes response", async () => {
    mockGetMyProfileLikes.mockResolvedValue(MOCK_LIKES);

    render(<FavoritesPage />);

    await waitFor(() => {
      expect(screen.getByText("Sarah Chen")).toBeInTheDocument();
    });
    expect(screen.getByText("Alex Patel")).toBeInTheDocument();
    expect(screen.getByText("Met at: AI Mixer")).toBeInTheDocument();
    expect(screen.getByText("Met at: Unknown event")).toBeInTheDocument();
  });

  it("filters favorites by search query", async () => {
    mockGetMyProfileLikes.mockResolvedValue(MOCK_LIKES);

    render(<FavoritesPage />);

    await waitFor(() => {
      expect(screen.getByText("Sarah Chen")).toBeInTheDocument();
    });

    await userEvent.type(screen.getByPlaceholderText("Search favorites"), "alex");
    expect(screen.queryByText("Sarah Chen")).not.toBeInTheDocument();
    expect(screen.getByText("Alex Patel")).toBeInTheDocument();
  });

  it("navigates to profile details with source=favorites and event_id", async () => {
    mockGetMyProfileLikes.mockResolvedValue([MOCK_LIKES[0]]);

    render(<FavoritesPage />);

    await waitFor(() => {
      expect(screen.getByText("Sarah Chen")).toBeInTheDocument();
    });

    await userEvent.click(screen.getByText("Sarah Chen"));
    expect(mockPush).toHaveBeenCalledWith("/profile/liked-1?event_id=evt-1&source=favorites");
  });

  it("shows confirmation dialog before unliking from favorites", async () => {
    mockGetMyProfileLikes.mockResolvedValue([MOCK_LIKES[0]]);
    mockUnlikeProfile.mockResolvedValue(undefined);

    render(<FavoritesPage />);

    await waitFor(() => {
      expect(screen.getByText("Sarah Chen")).toBeInTheDocument();
    });

    const unlikeButton = screen.getByRole("button", { name: "Unlike profile" });
    await userEvent.click(unlikeButton);

    expect(screen.getByText("Remove Favorite?")).toBeInTheDocument();
    expect(mockUnlikeProfile).not.toHaveBeenCalled();

    await userEvent.click(screen.getByRole("button", { name: "Remove" }));
    await waitFor(() => {
      expect(mockUnlikeProfile).toHaveBeenCalledWith("liked-1");
    });
  });
});

