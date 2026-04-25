import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  mockPush,
  mockRefresh,
  resetNavigationMocks,
} from "@/test/mocks/next-navigation";
import {
  mockSignOut,
  resetSupabaseMocks,
  mockSessionWith,
  mockNoSession,
} from "@/test/mocks/supabase";

const mockGetMyEventConsent = vi.fn();
const mockGetCompatibility = vi.fn();

vi.mock("@/lib/api", () => ({
  api: {
    setToken: vi.fn(),
    getMyEventConsent: (...args: unknown[]) => mockGetMyEventConsent(...args),
    getCompatibility: (...args: unknown[]) => mockGetCompatibility(...args),
  },
}));

vi.mock("@/lib/consent-cache", () => ({
  getCachedEventConsent: vi.fn().mockReturnValue(null),
  setCachedEventConsent: vi.fn(),
}));

vi.mock("@/components/aurora", () => ({
  Aurora: () => <div data-testid="aurora" />,
}));

const mockSocketConnect = vi.fn();
const mockSocketDisconnect = vi.fn();
const mockSocketSend = vi.fn().mockReturnValue(true);
const mockSocketOnMessage = vi.fn().mockReturnValue(vi.fn());
const mockSocketIsConnected = vi.fn().mockReturnValue(false);

vi.mock("@/lib/socket", () => {
  function MockSocketClient() {
    return {
      connect: mockSocketConnect,
      disconnect: mockSocketDisconnect,
      send: mockSocketSend,
      onMessage: mockSocketOnMessage,
      isConnected: mockSocketIsConnected,
    };
  }
  return { SocketClient: MockSocketClient };
});

const MOCK_RECOGNITION_RESULT = {
  id: "user-abc",
  user_id: "user-abc",
  matched_user_id: "user-abc",
  confidence: 92.5,
  created_at: new Date().toISOString(),
  profile: {
    user_id: "user-abc",
    full_name: "Sarah Chen",
    headline: "ML Engineer at OpenAI",
    bio: "Passionate about AI",
    location: "San Francisco",
    company: "OpenAI",
    major: "Computer Science",
    graduation_year: 2021,
    linkedin_url: "https://linkedin.com/in/sarachen",
    photo_path: null,
    experiences: [],
    education: [],
    profile_one_liner: "Building the future of AI",
    profile_summary: null,
  },
};

import RecognitionPage from "../page";

describe("RecognitionPage", () => {
  beforeEach(() => {
    resetNavigationMocks();
    resetSupabaseMocks();
    mockGetMyEventConsent.mockClear();
    mockGetCompatibility.mockClear();
    mockSocketConnect.mockClear();
    mockSocketDisconnect.mockClear();
    mockSocketSend.mockClear();
    mockSocketOnMessage.mockClear().mockReturnValue(vi.fn());
    mockSocketIsConnected.mockClear().mockReturnValue(false);
    mockSignOut.mockClear();
    sessionStorage.clear();
  });

  it("shows loading spinner initially", () => {
    mockSessionWith();
    mockGetMyEventConsent.mockResolvedValue({
      allow_profile_display: true,
      allow_recognition: true,
    });

    render(<RecognitionPage />);

    const spinners = document.querySelectorAll(".animate-spin");
    expect(spinners.length).toBeGreaterThan(0);
  });

  it("renders Recognition Feed heading after loading", async () => {
    mockSessionWith();
    mockGetMyEventConsent.mockResolvedValue({
      allow_profile_display: true,
      allow_recognition: true,
    });

    render(<RecognitionPage />);

    await waitFor(() => {
      expect(screen.getByText("Recognition Feed")).toBeInTheDocument();
    });
  });

  it("shows empty state when no results", async () => {
    mockSessionWith();
    mockGetMyEventConsent.mockResolvedValue({
      allow_profile_display: true,
      allow_recognition: true,
    });

    render(<RecognitionPage />);

    await waitFor(() => {
      expect(screen.getByText("Waiting for recognitions...")).toBeInTheDocument();
    });
    expect(screen.getByText("Results appear here in real-time")).toBeInTheDocument();
  });

  it("renders recognition card when results are cached in sessionStorage", async () => {
    sessionStorage.setItem(
      "recognition_results_cache",
      JSON.stringify([MOCK_RECOGNITION_RESULT]),
    );
    mockSessionWith();
    mockGetMyEventConsent.mockResolvedValue({
      allow_profile_display: true,
      allow_recognition: true,
    });
    mockGetCompatibility.mockResolvedValue({
      score: 0,
      shared_companies: [],
      shared_schools: [],
      shared_fields: [],
      conversation_starters: [],
    });

    render(<RecognitionPage />);

    await waitFor(() => {
      expect(screen.getByText("Sarah Chen")).toBeInTheDocument();
    });
  });

  it("displays confidence score on recognition card", async () => {
    sessionStorage.setItem(
      "recognition_results_cache",
      JSON.stringify([MOCK_RECOGNITION_RESULT]),
    );
    mockSessionWith();
    mockGetMyEventConsent.mockResolvedValue({
      allow_profile_display: true,
      allow_recognition: true,
    });
    mockGetCompatibility.mockResolvedValue({
      score: 0,
      shared_companies: [],
      shared_schools: [],
      shared_fields: [],
      conversation_starters: [],
    });

    render(<RecognitionPage />);

    await waitFor(() => {
      expect(screen.getByText("93%")).toBeInTheDocument();
    });
  });

  it("shows initials when no photo on recognition card", async () => {
    sessionStorage.setItem(
      "recognition_results_cache",
      JSON.stringify([MOCK_RECOGNITION_RESULT]),
    );
    mockSessionWith();
    mockGetMyEventConsent.mockResolvedValue({
      allow_profile_display: true,
      allow_recognition: true,
    });
    mockGetCompatibility.mockResolvedValue({
      score: 0,
      shared_companies: [],
      shared_schools: [],
      shared_fields: [],
      conversation_starters: [],
    });

    render(<RecognitionPage />);

    await waitFor(() => {
      expect(screen.getByText("SC")).toBeInTheDocument();
    });
  });

  it("navigates to profile page when clicking a recognition card", async () => {
    sessionStorage.setItem(
      "recognition_results_cache",
      JSON.stringify([MOCK_RECOGNITION_RESULT]),
    );
    mockSessionWith();
    mockGetMyEventConsent.mockResolvedValue({
      allow_profile_display: true,
      allow_recognition: true,
    });
    mockGetCompatibility.mockResolvedValue({
      score: 0,
      shared_companies: [],
      shared_schools: [],
      shared_fields: [],
      conversation_starters: [],
    });

    render(<RecognitionPage />);

    await waitFor(() => {
      expect(screen.getByText("Sarah Chen")).toBeInTheDocument();
    });

    await userEvent.click(screen.getByText("Sarah Chen"));

    expect(mockPush).toHaveBeenCalledWith("/profile/user-abc");
  });

  it("caches profile to sessionStorage when clicking a card", async () => {
    sessionStorage.setItem(
      "recognition_results_cache",
      JSON.stringify([MOCK_RECOGNITION_RESULT]),
    );
    mockSessionWith();
    mockGetMyEventConsent.mockResolvedValue({
      allow_profile_display: true,
      allow_recognition: true,
    });
    mockGetCompatibility.mockResolvedValue({
      score: 0,
      shared_companies: [],
      shared_schools: [],
      shared_fields: [],
      conversation_starters: [],
    });

    render(<RecognitionPage />);

    await waitFor(() => {
      expect(screen.getByText("Sarah Chen")).toBeInTheDocument();
    });

    await userEvent.click(screen.getByText("Sarah Chen"));

    const cached = sessionStorage.getItem("profile_cache_user-abc");
    expect(cached).not.toBeNull();
    expect(JSON.parse(cached!).full_name).toBe("Sarah Chen");
  });

  it("renders camera mode toggle button", async () => {
    mockSessionWith();
    mockGetMyEventConsent.mockResolvedValue({
      allow_profile_display: true,
      allow_recognition: true,
    });

    render(<RecognitionPage />);

    await waitFor(() => {
      expect(screen.getByText("Glasses")).toBeInTheDocument();
    });
  });

  it("switches to phone camera mode when toggle is clicked", async () => {
    mockSessionWith();
    mockGetMyEventConsent.mockResolvedValue({
      allow_profile_display: true,
      allow_recognition: true,
    });

    render(<RecognitionPage />);

    await waitFor(() => {
      expect(screen.getByText("Glasses")).toBeInTheDocument();
    });

    await userEvent.click(screen.getByText("Glasses"));

    expect(screen.getByText("Phone")).toBeInTheDocument();
  });

  it("renders scan button", async () => {
    mockSessionWith();
    mockGetMyEventConsent.mockResolvedValue({
      allow_profile_display: true,
      allow_recognition: true,
    });

    render(<RecognitionPage />);

    await waitFor(() => {
      expect(screen.getByText("Scan")).toBeInTheDocument();
    });
  });

  it("shows consent warning when consents are off", async () => {
    vi.stubEnv("NEXT_PUBLIC_RECOGNITION_EVENT_ID", "evt-123");
    mockSessionWith();
    mockGetMyEventConsent.mockResolvedValue({
      allow_profile_display: false,
      allow_recognition: false,
    });

    render(<RecognitionPage />);

    await waitFor(() => {
      expect(
        screen.getByText(
          "One or more event consents are off. You will not be able to recognize other attendees.",
        ),
      ).toBeInTheDocument();
    });

    vi.unstubAllEnvs();
  });

  it("does not show consent warning when consents are on", async () => {
    vi.stubEnv("NEXT_PUBLIC_RECOGNITION_EVENT_ID", "evt-123");
    mockSessionWith();
    mockGetMyEventConsent.mockResolvedValue({
      allow_profile_display: true,
      allow_recognition: true,
    });

    render(<RecognitionPage />);

    await waitFor(() => {
      expect(screen.getByText("Waiting for recognitions...")).toBeInTheDocument();
    });

    expect(
      screen.queryByText(
        "One or more event consents are off. You will not be able to recognize other attendees.",
      ),
    ).not.toBeInTheDocument();

    vi.unstubAllEnvs();
  });

  it("renders sign out button", async () => {
    mockSessionWith();
    mockGetMyEventConsent.mockResolvedValue({
      allow_profile_display: true,
      allow_recognition: true,
    });

    render(<RecognitionPage />);

    await waitFor(() => {
      expect(screen.getByText("Sign Out")).toBeInTheDocument();
    });
  });

  it("calls sign out and redirects when sign out is clicked", async () => {
    mockSessionWith();
    mockSignOut.mockResolvedValue({ error: null });
    mockGetMyEventConsent.mockResolvedValue({
      allow_profile_display: true,
      allow_recognition: true,
    });

    render(<RecognitionPage />);

    await waitFor(() => {
      expect(screen.getByText("Sign Out")).toBeInTheDocument();
    });

    await userEvent.click(screen.getByText("Sign Out"));

    await waitFor(() => {
      expect(mockSignOut).toHaveBeenCalled();
      expect(mockPush).toHaveBeenCalledWith("/");
    });
  });

  it("connects socket with access token on init", async () => {
    mockSessionWith("my-test-token");
    mockGetMyEventConsent.mockResolvedValue({
      allow_profile_display: true,
      allow_recognition: true,
    });

    render(<RecognitionPage />);

    await waitFor(() => {
      expect(mockSocketConnect).toHaveBeenCalledWith("my-test-token");
    });
  });

  it("does not connect socket when no session", async () => {
    mockNoSession();

    render(<RecognitionPage />);

    await waitFor(() => {
      expect(screen.getByText("Waiting for recognitions...")).toBeInTheDocument();
    });

    expect(mockSocketConnect).not.toHaveBeenCalled();
  });

  it("displays compatibility score when available", async () => {
    const resultWithCompat = {
      ...MOCK_RECOGNITION_RESULT,
      compatibility: {
        score: 78,
        shared_companies: [],
        shared_schools: ["Purdue University"],
        shared_fields: [],
        conversation_starters: ["Ask about their Purdue experience"],
      },
    };
    sessionStorage.setItem(
      "recognition_results_cache",
      JSON.stringify([resultWithCompat]),
    );
    mockSessionWith();
    mockGetMyEventConsent.mockResolvedValue({
      allow_profile_display: true,
      allow_recognition: true,
    });
    mockGetCompatibility.mockResolvedValue(resultWithCompat.compatibility);

    render(<RecognitionPage />);

    await waitFor(() => {
      expect(screen.getByText("78% match")).toBeInTheDocument();
    });
  });

  it("displays shared schools from compatibility data", async () => {
    const resultWithCompat = {
      ...MOCK_RECOGNITION_RESULT,
      compatibility: {
        score: 65,
        shared_companies: [],
        shared_schools: ["Purdue University"],
        shared_fields: ["Machine Learning"],
        conversation_starters: [],
      },
    };
    sessionStorage.setItem(
      "recognition_results_cache",
      JSON.stringify([resultWithCompat]),
    );
    mockSessionWith();
    mockGetMyEventConsent.mockResolvedValue({
      allow_profile_display: true,
      allow_recognition: true,
    });
    mockGetCompatibility.mockResolvedValue(resultWithCompat.compatibility);

    render(<RecognitionPage />);

    await waitFor(() => {
      expect(screen.getByText(/Purdue University/)).toBeInTheDocument();
    });
  });

  it("displays conversation starter when available", async () => {
    const resultWithStarter = {
      ...MOCK_RECOGNITION_RESULT,
      compatibility: {
        score: 50,
        shared_companies: [],
        shared_schools: [],
        shared_fields: [],
        conversation_starters: ["Ask about their AI research"],
      },
    };
    sessionStorage.setItem(
      "recognition_results_cache",
      JSON.stringify([resultWithStarter]),
    );
    mockSessionWith();
    mockGetMyEventConsent.mockResolvedValue({
      allow_profile_display: true,
      allow_recognition: true,
    });
    mockGetCompatibility.mockResolvedValue(resultWithStarter.compatibility);

    render(<RecognitionPage />);

    await waitFor(() => {
      expect(screen.getByText(/Ask about their AI research/)).toBeInTheDocument();
    });
  });
});
