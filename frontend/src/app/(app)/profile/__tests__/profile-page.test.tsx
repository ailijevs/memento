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
} from "@/test/mocks/supabase";

const mockGetProfile = vi.fn();
const mockUpdateProfile = vi.fn();
const mockGetMyNotificationPreferences = vi.fn();
const mockUpdateMyNotificationPreferences = vi.fn();

vi.mock("@/lib/api", () => ({
  api: {
    setToken: vi.fn(),
    getProfile: (...args: unknown[]) => mockGetProfile(...args),
    updateProfile: (...args: unknown[]) => mockUpdateProfile(...args),
    getMyNotificationPreferences: (...args: unknown[]) =>
      mockGetMyNotificationPreferences(...args),
    updateMyNotificationPreferences: (...args: unknown[]) =>
      mockUpdateMyNotificationPreferences(...args),
  },
}));

vi.mock("@/lib/profile-photo-upload", () => ({
  uploadProfilePhoto: vi.fn(),
}));

vi.mock("@/lib/use-profile-photo-url", () => ({
  useProfilePhotoUrl: (path: string | null) => ({
    photoUrl: path,
    handleImageError: vi.fn(),
  }),
}));

vi.mock("@/components/aurora", () => ({
  Aurora: () => <div data-testid="aurora" />,
}));

const MOCK_PROFILE = {
  user_id: "user-1",
  full_name: "Jane Smith",
  headline: "Product Manager",
  bio: "I build things",
  location: "New York",
  company: "Acme Corp",
  major: "Business",
  graduation_year: 2022,
  linkedin_url: "https://linkedin.com/in/jane",
  photo_path: null,
  experiences: [
    {
      company: "Acme Corp",
      title: "PM",
      start_date: "2022-01",
      end_date: null,
      description: null,
      location: null,
    },
  ],
  education: [
    {
      school: "NYU",
      degree: "MBA",
      field_of_study: "Business",
      start_date: "2020",
      end_date: "2022",
    },
  ],
  profile_one_liner: null,
  profile_summary: null,
};

const DEFAULT_PREFS = {
  email_notifications: true,
  event_updates: true,
  host_messages: true,
};

import ProfilePage from "../page";

describe("ProfilePage", () => {
  beforeEach(() => {
    resetNavigationMocks();
    resetSupabaseMocks();
    mockGetProfile.mockClear();
    mockUpdateProfile.mockClear();
    mockGetMyNotificationPreferences.mockClear();
    mockUpdateMyNotificationPreferences.mockClear();
    mockSignOut.mockClear();
    mockGetMyNotificationPreferences.mockResolvedValue(DEFAULT_PREFS);
    mockUpdateMyNotificationPreferences.mockImplementation(
      (updates: Partial<typeof DEFAULT_PREFS>) => ({
        ...DEFAULT_PREFS,
        ...updates,
      })
    );
  });

  it("renders profile data after loading", async () => {
    mockSessionWith();
    mockGetProfile.mockResolvedValue(MOCK_PROFILE);

    render(<ProfilePage />);

    await waitFor(() => {
      expect(screen.getByText("Jane Smith")).toBeInTheDocument();
    });

    expect(screen.getByText("Product Manager")).toBeInTheDocument();
    expect(screen.getByText("I build things")).toBeInTheDocument();
    expect(screen.getByText("New York")).toBeInTheDocument();
  });

  it("shows initials when no photo", async () => {
    mockSessionWith();
    mockGetProfile.mockResolvedValue(MOCK_PROFILE);

    render(<ProfilePage />);

    await waitFor(() => {
      expect(screen.getByText("JS")).toBeInTheDocument();
    });
  });

  it("renders section labels", async () => {
    mockSessionWith();
    mockGetProfile.mockResolvedValue(MOCK_PROFILE);

    render(<ProfilePage />);

    await waitFor(() => {
      expect(screen.getByText("About")).toBeInTheDocument();
    });
    expect(screen.getByText("Location")).toBeInTheDocument();
    expect(screen.getByText("Work")).toBeInTheDocument();
    expect(screen.getByText("Education")).toBeInTheDocument();
  });

  it("renders experience entries", async () => {
    mockSessionWith();
    mockGetProfile.mockResolvedValue(MOCK_PROFILE);

    render(<ProfilePage />);

    await waitFor(() => {
      expect(screen.getByText("PM")).toBeInTheDocument();
    });
  });

  it("renders education entries", async () => {
    mockSessionWith();
    mockGetProfile.mockResolvedValue(MOCK_PROFILE);

    render(<ProfilePage />);

    await waitFor(() => {
      expect(screen.getByText("NYU")).toBeInTheDocument();
    });
    expect(screen.getByText("MBA, Business")).toBeInTheDocument();
  });

  it("shows sign out button", async () => {
    mockSessionWith();
    mockGetProfile.mockResolvedValue(MOCK_PROFILE);

    render(<ProfilePage />);

    await waitFor(() => {
      expect(screen.getByText("Profile Info")).toBeInTheDocument();
    });

    expect(screen.queryByText("Sign Out")).not.toBeInTheDocument();

    await userEvent.click(screen.getByText("Account Settings"));

    expect(screen.getByText("Sign Out")).toBeInTheDocument();
  });

  it("shows sign out confirmation when clicked", async () => {
    mockSessionWith();
    mockGetProfile.mockResolvedValue(MOCK_PROFILE);

    render(<ProfilePage />);

    await waitFor(() => {
      expect(screen.getByText("Account Settings")).toBeInTheDocument();
    });

    await userEvent.click(screen.getByText("Account Settings"));
    await userEvent.click(screen.getByText("Sign Out"));

    expect(screen.getByText("Yes, sign out")).toBeInTheDocument();
    expect(screen.getByText("Cancel")).toBeInTheDocument();
  });

  it("cancels sign out confirmation", async () => {
    mockSessionWith();
    mockGetProfile.mockResolvedValue(MOCK_PROFILE);

    render(<ProfilePage />);

    await waitFor(() => {
      expect(screen.getByText("Account Settings")).toBeInTheDocument();
    });

    await userEvent.click(screen.getByText("Account Settings"));
    await userEvent.click(screen.getByText("Sign Out"));
    await userEvent.click(screen.getByText("Cancel"));

    expect(screen.queryByText("Yes, sign out")).not.toBeInTheDocument();
    expect(screen.getByText("Sign Out")).toBeInTheDocument();
  });

  it("calls supabase signOut and redirects", async () => {
    mockSessionWith();
    mockGetProfile.mockResolvedValue(MOCK_PROFILE);
    mockSignOut.mockResolvedValue({ error: null });

    render(<ProfilePage />);

    await waitFor(() => {
      expect(screen.getByText("Account Settings")).toBeInTheDocument();
    });

    await userEvent.click(screen.getByText("Account Settings"));
    await userEvent.click(screen.getByText("Sign Out"));
    await userEvent.click(screen.getByText("Yes, sign out"));

    await waitFor(() => {
      expect(mockSignOut).toHaveBeenCalled();
      expect(mockPush).toHaveBeenCalledWith("/");
    });
  });

  it("opens edit mode when clicking a field", async () => {
    mockSessionWith();
    mockGetProfile.mockResolvedValue(MOCK_PROFILE);

    render(<ProfilePage />);

    await waitFor(() => {
      expect(screen.getByText("I build things")).toBeInTheDocument();
    });

    await userEvent.click(screen.getByText("I build things"));

    expect(screen.getByDisplayValue("I build things")).toBeInTheDocument();
  });

  it("shows profile info tab by default and switches to account settings", async () => {
    mockSessionWith();
    mockGetProfile.mockResolvedValue(MOCK_PROFILE);

    render(<ProfilePage />);

    await waitFor(() => {
      expect(screen.getByText("About")).toBeInTheDocument();
    });
    expect(screen.queryByText("Email Notifications")).not.toBeInTheDocument();

    await userEvent.click(screen.getByText("Account Settings"));

    expect(screen.getByText("Email Notifications")).toBeInTheDocument();
    expect(screen.getByText("Event Updates")).toBeInTheDocument();
    expect(screen.getByText("Host Messages")).toBeInTheDocument();
    expect(screen.queryByText("About")).not.toBeInTheDocument();
  });

  it("updates notification preference toggle", async () => {
    mockSessionWith();
    mockGetProfile.mockResolvedValue(MOCK_PROFILE);
    mockGetMyNotificationPreferences.mockResolvedValue({
      ...DEFAULT_PREFS,
      event_updates: true,
    });
    mockUpdateMyNotificationPreferences.mockResolvedValue({
      ...DEFAULT_PREFS,
      event_updates: false,
    });

    render(<ProfilePage />);

    await waitFor(() => {
      expect(screen.getByText("Account Settings")).toBeInTheDocument();
    });

    await userEvent.click(screen.getByText("Account Settings"));

    const eventUpdatesSwitch = screen.getByRole("switch", {
      name: "Event Updates",
    });
    expect(eventUpdatesSwitch).toHaveAttribute("aria-checked", "true");

    await userEvent.click(eventUpdatesSwitch);

    await waitFor(() => {
      expect(mockUpdateMyNotificationPreferences).toHaveBeenCalledWith({
        event_updates: false,
      });
    });
    expect(eventUpdatesSwitch).toHaveAttribute("aria-checked", "false");
  });
});
