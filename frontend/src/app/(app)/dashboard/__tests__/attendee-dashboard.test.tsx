import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { createRef } from "react";
import { AttendeeContent, AttendeeControls } from "../attendee-dashboard";
import type { AttendeeEventItem } from "../attendee-dashboard";

const MOCK_EVENT = {
  event_id: "evt-1",
  created_by: "org-1",
  name: "Tech Meetup",
  starts_at: new Date(Date.now() - 3600000).toISOString(),
  ends_at: new Date(Date.now() + 86400000).toISOString(),
  location: "Room 101",
  description: "A tech meetup",
  max_participants: 50,
  is_active: true,
  indexing_status: "completed" as const,
  cleanup_status: "pending" as const,
  created_at: "2026-01-01T00:00:00Z",
};

const FUTURE_EVENT = {
  ...MOCK_EVENT,
  event_id: "evt-2",
  name: "Future Conference",
  starts_at: new Date(Date.now() + 86400000).toISOString(),
};

describe("AttendeeControls", () => {
  it("renders search input and discover button", () => {
    render(
      <AttendeeControls
        searchText=""
        onSearchTextChange={vi.fn()}
        onOpenDiscover={vi.fn()}
      />,
    );

    expect(screen.getByPlaceholderText("Search your events")).toBeInTheDocument();
    expect(screen.getByText("Discover Events")).toBeInTheDocument();
  });

  it("calls onSearchTextChange when typing", async () => {
    const onSearchTextChange = vi.fn();
    render(
      <AttendeeControls
        searchText=""
        onSearchTextChange={onSearchTextChange}
        onOpenDiscover={vi.fn()}
      />,
    );

    await userEvent.type(screen.getByPlaceholderText("Search your events"), "test");
    expect(onSearchTextChange).toHaveBeenCalled();
  });

  it("calls onOpenDiscover when button is clicked", async () => {
    const onOpenDiscover = vi.fn();
    render(
      <AttendeeControls
        searchText=""
        onSearchTextChange={vi.fn()}
        onOpenDiscover={onOpenDiscover}
      />,
    );

    await userEvent.click(screen.getByText("Discover Events"));
    expect(onOpenDiscover).toHaveBeenCalledOnce();
  });
});

describe("AttendeeContent", () => {
  const defaultProps = {
    openEventMenuId: null,
    openMenuContainerRef: createRef<HTMLDivElement>(),
    leavingEventId: null,
    onToggleEventMenu: vi.fn(),
    onViewEventDetail: vi.fn(),
    onViewRsvpList: vi.fn(),
    onEditConsents: vi.fn(),
    onLeaveEvent: vi.fn(),
    onStartRecognition: vi.fn(),
    formatEventDate: (v: string) => new Date(v).toLocaleDateString(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows loading spinner when loading", () => {
    render(<AttendeeContent {...defaultProps} loading={true} events={[]} />);

    const spinners = document.querySelectorAll(".animate-spin");
    expect(spinners.length).toBeGreaterThan(0);
  });

  it("shows empty state when no events", () => {
    render(<AttendeeContent {...defaultProps} loading={false} events={[]} />);

    expect(screen.getByText("No upcoming events found")).toBeInTheDocument();
  });

  it("renders event cards with name and location", () => {
    const items: AttendeeEventItem[] = [{ event: MOCK_EVENT, hasStarted: true }];
    render(<AttendeeContent {...defaultProps} loading={false} events={items} />);

    expect(screen.getByText("Tech Meetup")).toBeInTheDocument();
    expect(screen.getByText("Room 101")).toBeInTheDocument();
  });

  it("shows Start Recognition button for started events", () => {
    const items: AttendeeEventItem[] = [{ event: MOCK_EVENT, hasStarted: true }];
    render(<AttendeeContent {...defaultProps} loading={false} events={items} />);

    expect(screen.getByText("Start Recognition")).toBeInTheDocument();
  });

  it("shows message for future events that haven't started", () => {
    const items: AttendeeEventItem[] = [{ event: FUTURE_EVENT, hasStarted: false }];
    render(<AttendeeContent {...defaultProps} loading={false} events={items} />);

    expect(screen.getByText("Recognition opens when this event starts")).toBeInTheDocument();
  });

  it("shows overflow menu with options when opened", () => {
    const items: AttendeeEventItem[] = [{ event: MOCK_EVENT, hasStarted: true }];
    render(
      <AttendeeContent
        {...defaultProps}
        loading={false}
        events={items}
        openEventMenuId="evt-1"
      />,
    );

    expect(screen.getByText("RSVP List")).toBeInTheDocument();
    expect(screen.getByText("Edit Consents")).toBeInTheDocument();
    expect(screen.getByText("Leave Event")).toBeInTheDocument();
  });

  it("calls onLeaveEvent when Leave Event is clicked", async () => {
    const onLeaveEvent = vi.fn();
    const items: AttendeeEventItem[] = [{ event: MOCK_EVENT, hasStarted: true }];
    render(
      <AttendeeContent
        {...defaultProps}
        loading={false}
        events={items}
        openEventMenuId="evt-1"
        onLeaveEvent={onLeaveEvent}
      />,
    );

    await userEvent.click(screen.getByText("Leave Event"));
    expect(onLeaveEvent).toHaveBeenCalledWith(MOCK_EVENT);
  });

  it("calls onEditConsents when Edit Consents is clicked", async () => {
    const onEditConsents = vi.fn();
    const items: AttendeeEventItem[] = [{ event: MOCK_EVENT, hasStarted: true }];
    render(
      <AttendeeContent
        {...defaultProps}
        loading={false}
        events={items}
        openEventMenuId="evt-1"
        onEditConsents={onEditConsents}
      />,
    );

    await userEvent.click(screen.getByText("Edit Consents"));
    expect(onEditConsents).toHaveBeenCalledWith(MOCK_EVENT);
  });

  it("calls onStartRecognition when Start Recognition is clicked", async () => {
    const onStartRecognition = vi.fn();
    const items: AttendeeEventItem[] = [{ event: MOCK_EVENT, hasStarted: true }];
    render(
      <AttendeeContent
        {...defaultProps}
        loading={false}
        events={items}
        onStartRecognition={onStartRecognition}
      />,
    );

    await userEvent.click(screen.getByText("Start Recognition"));
    expect(onStartRecognition).toHaveBeenCalledWith(MOCK_EVENT);
  });

  it("shows Leaving state when leavingEventId matches", () => {
    const items: AttendeeEventItem[] = [{ event: MOCK_EVENT, hasStarted: true }];
    render(
      <AttendeeContent
        {...defaultProps}
        loading={false}
        events={items}
        openEventMenuId="evt-1"
        leavingEventId="evt-1"
      />,
    );

    expect(screen.getByText("Leaving")).toBeInTheDocument();
  });
});
