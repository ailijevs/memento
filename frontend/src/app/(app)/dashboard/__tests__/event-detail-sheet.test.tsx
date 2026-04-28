import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { EventDetailSheetContent } from "../event-detail-sheet-content";

const MOCK_EVENT = {
  event_id: "evt-1",
  created_by: "org-1",
  name: "Spring Demo Day",
  starts_at: "2026-05-15T14:00:00Z",
  ends_at: "2026-05-15T18:00:00Z",
  location: "Engineering Hall 101",
  description: "Annual ECE demo day showcase",
  max_participants: 200,
  is_active: true,
  indexing_status: "completed" as const,
  cleanup_status: "pending" as const,
  created_at: "2026-01-01T00:00:00Z",
};

const formatEventDate = (v: string) =>
  new Date(v).toLocaleString("en-US", { dateStyle: "medium", timeStyle: "short" });

describe("EventDetailSheetContent", () => {
  it("renders event name", () => {
    render(<EventDetailSheetContent event={MOCK_EVENT} formatEventDate={formatEventDate} />);
    expect(screen.getByText("Spring Demo Day")).toBeInTheDocument();
  });

  it("renders location", () => {
    render(<EventDetailSheetContent event={MOCK_EVENT} formatEventDate={formatEventDate} />);
    expect(screen.getByText("Engineering Hall 101")).toBeInTheDocument();
  });

  it("renders description", () => {
    render(<EventDetailSheetContent event={MOCK_EVENT} formatEventDate={formatEventDate} />);
    expect(screen.getByText("Annual ECE demo day showcase")).toBeInTheDocument();
    expect(screen.getByText("Description")).toBeInTheDocument();
  });

  it("renders max participants", () => {
    render(<EventDetailSheetContent event={MOCK_EVENT} formatEventDate={formatEventDate} />);
    expect(screen.getByText("200")).toBeInTheDocument();
    expect(screen.getByText("Max Participants")).toBeInTheDocument();
  });

  it("renders start and end labels", () => {
    render(<EventDetailSheetContent event={MOCK_EVENT} formatEventDate={formatEventDate} />);
    expect(screen.getByText("Starts")).toBeInTheDocument();
    expect(screen.getByText("Ends")).toBeInTheDocument();
  });

  it("shows Inactive badge when event is not active", () => {
    const inactiveEvent = { ...MOCK_EVENT, is_active: false };
    render(<EventDetailSheetContent event={inactiveEvent} formatEventDate={formatEventDate} />);
    expect(screen.getByText("Inactive")).toBeInTheDocument();
  });

  it("does not show Inactive badge when event is active", () => {
    render(<EventDetailSheetContent event={MOCK_EVENT} formatEventDate={formatEventDate} />);
    expect(screen.queryByText("Inactive")).not.toBeInTheDocument();
  });

  it("hides description section when no description", () => {
    const noDesc = { ...MOCK_EVENT, description: null };
    render(<EventDetailSheetContent event={noDesc} formatEventDate={formatEventDate} />);
    expect(screen.queryByText("Description")).not.toBeInTheDocument();
  });

  it("hides max participants when not set", () => {
    const noMax = { ...MOCK_EVENT, max_participants: null };
    render(<EventDetailSheetContent event={noMax} formatEventDate={formatEventDate} />);
    expect(screen.queryByText("Max Participants")).not.toBeInTheDocument();
  });
});
