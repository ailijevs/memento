import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { OrganizerControls, OrganizerContent } from "../organizer-dashboard";

const ACTIVE_EVENT = {
  event_id: "evt-org-1",
  created_by: "user-1",
  name: "Spring Demo Day",
  starts_at: new Date(Date.now() + 86400000).toISOString(),
  ends_at: new Date(Date.now() + 172800000).toISOString(),
  location: "Main Hall",
  description: "Annual demo day",
  max_participants: 100,
  is_active: true,
  indexing_status: "completed" as const,
  cleanup_status: "pending" as const,
  created_at: "2026-01-01T00:00:00Z",
};

const INACTIVE_EVENT = {
  ...ACTIVE_EVENT,
  event_id: "evt-org-2",
  name: "Archived Workshop",
  is_active: false,
};

describe("OrganizerControls", () => {
  it("renders Create Event button", () => {
    render(<OrganizerControls onCreateEvent={vi.fn()} />);
    expect(screen.getByText("Create Event")).toBeInTheDocument();
  });

  it("calls onCreateEvent when clicked", async () => {
    const onCreateEvent = vi.fn();
    render(<OrganizerControls onCreateEvent={onCreateEvent} />);

    await userEvent.click(screen.getByText("Create Event"));
    expect(onCreateEvent).toHaveBeenCalledOnce();
  });
});

describe("OrganizerContent", () => {
  const defaultProps = {
    formatEventDate: (v: string) => new Date(v).toLocaleDateString(),
    deletingEventId: null,
    archivingEventId: null,
    unarchivingEventId: null,
    onViewEventDetail: vi.fn(),
    onEditEventRequest: vi.fn(),
    onViewRsvpList: vi.fn(),
    onArchiveEvent: vi.fn().mockResolvedValue(undefined),
    onUnarchiveEvent: vi.fn().mockResolvedValue(undefined),
    onDeleteEvent: vi.fn().mockResolvedValue(undefined),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows No active events when list is empty", () => {
    render(<OrganizerContent {...defaultProps} events={[]} />);
    expect(screen.getByText("No active events")).toBeInTheDocument();
  });

  it("renders active event name and location", () => {
    render(<OrganizerContent {...defaultProps} events={[ACTIVE_EVENT]} />);

    expect(screen.getByText("Spring Demo Day")).toBeInTheDocument();
    expect(screen.getByText("Main Hall")).toBeInTheDocument();
  });

  it("shows Active Events section header", () => {
    render(<OrganizerContent {...defaultProps} events={[ACTIVE_EVENT]} />);
    expect(screen.getByText("Active Events")).toBeInTheDocument();
  });

  it("shows Inactive Events section when inactive events exist", () => {
    render(<OrganizerContent {...defaultProps} events={[ACTIVE_EVENT, INACTIVE_EVENT]} />);

    expect(screen.getByText("Active Events")).toBeInTheDocument();
    expect(screen.getByText("Inactive Events")).toBeInTheDocument();
    expect(screen.getByText("Archived Workshop")).toBeInTheDocument();
  });

  it("shows overflow menu with edit, RSVP, archive, delete for active events", async () => {
    render(<OrganizerContent {...defaultProps} events={[ACTIVE_EVENT]} />);

    await userEvent.click(screen.getByLabelText("Organizer event actions"));

    expect(screen.getByText("Edit Event")).toBeInTheDocument();
    expect(screen.getByText("RSVP List")).toBeInTheDocument();
    expect(screen.getByText("Archive Event")).toBeInTheDocument();
    expect(screen.getByText("Delete Event")).toBeInTheDocument();
  });

  it("shows delete confirmation dialog when Delete Event is clicked", async () => {
    render(<OrganizerContent {...defaultProps} events={[ACTIVE_EVENT]} />);

    await userEvent.click(screen.getByLabelText("Organizer event actions"));
    await userEvent.click(screen.getByText("Delete Event"));

    expect(screen.getByText("Delete Event?")).toBeInTheDocument();
    expect(screen.getByText(/permanently delete "Spring Demo Day"/)).toBeInTheDocument();
  });

  it("shows archive confirmation dialog when Archive Event is clicked", async () => {
    render(<OrganizerContent {...defaultProps} events={[ACTIVE_EVENT]} />);

    await userEvent.click(screen.getByLabelText("Organizer event actions"));
    await userEvent.click(screen.getByText("Archive Event"));

    expect(screen.getByText("Archive Event?")).toBeInTheDocument();
    expect(screen.getByText(/hide "Spring Demo Day" from active events/)).toBeInTheDocument();
  });

  it("shows Unarchive Event option for inactive events", async () => {
    render(<OrganizerContent {...defaultProps} events={[INACTIVE_EVENT]} />);

    const buttons = screen.getAllByLabelText("Organizer event actions");
    await userEvent.click(buttons[0]);

    expect(screen.getByText("Unarchive Event")).toBeInTheDocument();
  });
});
