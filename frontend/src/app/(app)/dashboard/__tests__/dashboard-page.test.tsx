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

const mockGetMyEvents = vi.fn();
const mockGetMyOrganizedEvents = vi.fn();
const mockGetEvents = vi.fn();
const mockJoinEvent = vi.fn();
const mockLeaveEvent = vi.fn();
const mockCreateEvent = vi.fn();
const mockDeleteEvent = vi.fn();
const mockGetMyEventConsent = vi.fn();
const mockUpdateMyEventConsent = vi.fn();
const mockGetEventDirectory = vi.fn();

vi.mock("@/lib/api", () => ({
  api: {
    setToken: vi.fn(),
    getMyEvents: (...args: unknown[]) => mockGetMyEvents(...args),
    getMyOrganizedEvents: (...args: unknown[]) => mockGetMyOrganizedEvents(...args),
    getEvents: (...args: unknown[]) => mockGetEvents(...args),
    joinEvent: (...args: unknown[]) => mockJoinEvent(...args),
    leaveEvent: (...args: unknown[]) => mockLeaveEvent(...args),
    createEvent: (...args: unknown[]) => mockCreateEvent(...args),
    deleteEvent: (...args: unknown[]) => mockDeleteEvent(...args),
    getMyEventConsent: (...args: unknown[]) => mockGetMyEventConsent(...args),
    updateMyEventConsent: (...args: unknown[]) => mockUpdateMyEventConsent(...args),
    updateEvent: vi.fn(),
    getEventDirectory: (...args: unknown[]) => mockGetEventDirectory(...args),
  },
  ApiError: class extends Error {
    status: number;
    constructor(status: number, message: string) {
      super(message);
      this.status = status;
    }
  },
  isApiErrorWithStatus: (error: unknown, status: number) => {
    return error instanceof Error && "status" in error && (error as { status: number }).status === status;
  },
}));

vi.mock("@/lib/consent-cache", () => ({
  getCachedEventConsent: vi.fn().mockReturnValue(null),
  setCachedEventConsent: vi.fn(),
}));

vi.mock("@/components/aurora", () => ({
  Aurora: () => <div data-testid="aurora" />,
}));

const MOCK_EVENT = {
  event_id: "evt-1",
  created_by: "organizer-1",
  name: "Tech Meetup",
  starts_at: new Date(Date.now() + 86400000).toISOString(),
  ends_at: new Date(Date.now() + 172800000).toISOString(),
  location: "Room 101",
  description: "A tech meetup",
  max_participants: 50,
  is_active: true,
  indexing_status: "completed" as const,
  cleanup_status: "pending" as const,
  created_at: "2026-01-01T00:00:00Z",
};

const MOCK_ORGANIZED_EVENT = {
  ...MOCK_EVENT,
  event_id: "evt-org-1",
  created_by: "user-1",
  name: "My Organized Event",
};

import DashboardPage from "../page";

describe("DashboardPage", () => {
  beforeEach(() => {
    resetNavigationMocks();
    resetSupabaseMocks();
    mockGetMyEvents.mockClear();
    mockGetMyOrganizedEvents.mockClear();
    mockGetEvents.mockClear();
    mockSignOut.mockClear();
  });

  it("shows loading spinner initially", () => {
    mockSessionWith();
    mockGetMyEvents.mockImplementation(() => new Promise(() => {}));
    mockGetMyOrganizedEvents.mockImplementation(() => new Promise(() => {}));

    render(<DashboardPage />);

    const spinners = document.querySelectorAll(".animate-spin");
    expect(spinners.length).toBeGreaterThan(0);
  });

  it("renders events list after loading", async () => {
    mockSessionWith();
    mockGetMyEvents.mockResolvedValue([MOCK_EVENT]);
    mockGetMyOrganizedEvents.mockResolvedValue([]);

    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText("Tech Meetup")).toBeInTheDocument();
    });
  });

  it("renders event location", async () => {
    mockSessionWith();
    mockGetMyEvents.mockResolvedValue([MOCK_EVENT]);
    mockGetMyOrganizedEvents.mockResolvedValue([]);

    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText("Room 101")).toBeInTheDocument();
    });
  });

  it("shows empty state when no events", async () => {
    mockSessionWith();
    mockGetMyEvents.mockResolvedValue([]);
    mockGetMyOrganizedEvents.mockResolvedValue([]);

    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText("No upcoming events found")).toBeInTheDocument();
    });
  });

  it("renders Attendee and Organizer tab buttons", async () => {
    mockSessionWith();
    mockGetMyEvents.mockResolvedValue([MOCK_EVENT]);
    mockGetMyOrganizedEvents.mockResolvedValue([MOCK_ORGANIZED_EVENT]);

    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText("Attendee")).toBeInTheDocument();
    });
    expect(screen.getByText("Organizer")).toBeInTheDocument();
  });

  it("switches to organizer tab and shows organized events", async () => {
    mockSessionWith();
    mockGetMyEvents.mockResolvedValue([MOCK_EVENT]);
    mockGetMyOrganizedEvents.mockResolvedValue([MOCK_ORGANIZED_EVENT]);

    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText("Organizer")).toBeInTheDocument();
    });

    await userEvent.click(screen.getByText("Organizer"));

    await waitFor(() => {
      expect(screen.getByText("My Organized Event")).toBeInTheDocument();
    });
  });

  it("switches back to attendee tab", async () => {
    mockSessionWith();
    mockGetMyEvents.mockResolvedValue([MOCK_EVENT]);
    mockGetMyOrganizedEvents.mockResolvedValue([MOCK_ORGANIZED_EVENT]);

    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText("Organizer")).toBeInTheDocument();
    });

    await userEvent.click(screen.getByText("Organizer"));
    await userEvent.click(screen.getByText("Attendee"));

    await waitFor(() => {
      expect(screen.getByText("Tech Meetup")).toBeInTheDocument();
    });
  });

  it("renders sign out icon button", async () => {
    mockSessionWith();
    mockGetMyEvents.mockResolvedValue([]);
    mockGetMyOrganizedEvents.mockResolvedValue([]);

    render(<DashboardPage />);

    await waitFor(() => {
      const logOutIcons = document.querySelectorAll(".lucide-log-out");
      expect(logOutIcons.length).toBeGreaterThan(0);
    });
  });

  it("handles no session gracefully", async () => {
    mockNoSession();
    mockGetMyEvents.mockResolvedValue([]);
    mockGetMyOrganizedEvents.mockResolvedValue([]);

    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText("No upcoming events found")).toBeInTheDocument();
    });
  });

  it("renders discover and create buttons for organizer tab", async () => {
    mockSessionWith();
    mockGetMyEvents.mockResolvedValue([]);
    mockGetMyOrganizedEvents.mockResolvedValue([]);

    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText("Organizer")).toBeInTheDocument();
    });

    await userEvent.click(screen.getByText("Organizer"));

    await waitFor(() => {
      const plusIcons = document.querySelectorAll(".lucide-plus");
      expect(plusIcons.length).toBeGreaterThan(0);
    });
  });
});
