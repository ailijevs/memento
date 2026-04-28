import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import {
  CreateEventSheetContent,
  EditEventSheetContent,
} from "../create-event-sheet-content";

describe("CreateEventSheetContent", () => {
  it("renders all form fields", () => {
    render(<CreateEventSheetContent isSubmitting={false} onSubmit={vi.fn()} />);

    expect(screen.getByText("Event Name")).toBeInTheDocument();
    expect(screen.getByText("Location")).toBeInTheDocument();
    expect(screen.getByText("Description")).toBeInTheDocument();
    expect(screen.getByText("Max Participants")).toBeInTheDocument();
    expect(screen.getByText("Start Date")).toBeInTheDocument();
    expect(screen.getByText("Start Time")).toBeInTheDocument();
    expect(screen.getByText("End Date")).toBeInTheDocument();
    expect(screen.getByText("End Time")).toBeInTheDocument();
  });

  it("renders Create Event submit button", () => {
    render(<CreateEventSheetContent isSubmitting={false} onSubmit={vi.fn()} />);
    expect(screen.getByText("Create Event")).toBeInTheDocument();
  });

  it("disables submit button when required fields are empty", () => {
    render(<CreateEventSheetContent isSubmitting={false} onSubmit={vi.fn()} />);
    expect(screen.getByText("Create Event").closest("button")).toBeDisabled();
  });

  it("shows Creating text when submitting", () => {
    render(<CreateEventSheetContent isSubmitting={true} onSubmit={vi.fn()} />);
    expect(screen.getByText("Creating")).toBeInTheDocument();
  });

  it("accepts text in the name field", async () => {
    render(<CreateEventSheetContent isSubmitting={false} onSubmit={vi.fn()} />);

    const nameInput = screen.getByPlaceholderText("Spring Networking Mixer");
    await userEvent.type(nameInput, "My Event");

    expect(nameInput).toHaveValue("My Event");
  });

  it("accepts text in the location field", async () => {
    render(<CreateEventSheetContent isSubmitting={false} onSubmit={vi.fn()} />);

    const locationInput = screen.getByPlaceholderText("Austin Convention Center");
    await userEvent.type(locationInput, "Room 200");

    expect(locationInput).toHaveValue("Room 200");
  });

  it("accepts text in the description field", async () => {
    render(<CreateEventSheetContent isSubmitting={false} onSubmit={vi.fn()} />);

    const descInput = screen.getByPlaceholderText("Tell attendees what this event is about...");
    await userEvent.type(descInput, "A great event");

    expect(descInput).toHaveValue("A great event");
  });

  it("marks required fields with asterisk", () => {
    const { container } = render(
      <CreateEventSheetContent isSubmitting={false} onSubmit={vi.fn()} />,
    );

    const requiredMarkers = container.querySelectorAll(".text-red-300");
    expect(requiredMarkers.length).toBe(5);
  });

  it("autofills end date to match start date for new events", async () => {
    const { container } = render(
      <CreateEventSheetContent isSubmitting={false} onSubmit={vi.fn()} />,
    );

    const startDateInput = container.querySelector<HTMLInputElement>(
      "#create-event-start-date",
    );
    const endDateInput = container.querySelector<HTMLInputElement>(
      "#create-event-end-date",
    );

    expect(startDateInput).not.toBeNull();
    expect(endDateInput).not.toBeNull();
    fireEvent.change(startDateInput!, { target: { value: "2026-06-10" } });

    expect(endDateInput!).toHaveValue("2026-06-10");
  });

  it("autofills end time to one hour after start time for new events", async () => {
    const { container } = render(
      <CreateEventSheetContent isSubmitting={false} onSubmit={vi.fn()} />,
    );

    const startTimeInput = container.querySelector<HTMLInputElement>(
      "#create-event-start-time",
    );
    const endTimeInput = container.querySelector<HTMLInputElement>(
      "#create-event-end-time",
    );

    expect(startTimeInput).not.toBeNull();
    expect(endTimeInput).not.toBeNull();
    fireEvent.change(startTimeInput!, { target: { value: "09:30" } });

    expect(endTimeInput!).toHaveValue("10:30");
  });

  it("does not overwrite manually edited end time when start time changes", async () => {
    const { container } = render(
      <CreateEventSheetContent isSubmitting={false} onSubmit={vi.fn()} />,
    );

    const startTimeInput = container.querySelector<HTMLInputElement>(
      "#create-event-start-time",
    );
    const endTimeInput = container.querySelector<HTMLInputElement>(
      "#create-event-end-time",
    );

    expect(startTimeInput).not.toBeNull();
    expect(endTimeInput).not.toBeNull();

    fireEvent.change(startTimeInput!, { target: { value: "09:30" } });
    expect(endTimeInput!).toHaveValue("10:30");

    fireEvent.change(endTimeInput!, { target: { value: "11:15" } });
    fireEvent.change(startTimeInput!, { target: { value: "10:00" } });

    expect(endTimeInput!).toHaveValue("11:15");
  });
});

describe("EditEventSheetContent", () => {
  it("keeps existing end date/time values for edit mode", () => {
    const { container } = render(
      <EditEventSheetContent
        isSubmitting={false}
        onSubmit={vi.fn()}
        initialValues={{
          name: "Existing Event",
          starts_at: "2026-06-10T09:30:00",
          ends_at: "2026-06-10T12:00:00",
        }}
      />,
    );

    const startDateInput = container.querySelector("#edit-event-start-date");
    const endDateInput = container.querySelector("#edit-event-end-date");
    const startTimeInput = container.querySelector("#edit-event-start-time");
    const endTimeInput = container.querySelector("#edit-event-end-time");

    expect(startDateInput).toHaveValue("2026-06-10");
    expect(endDateInput).toHaveValue("2026-06-10");
    expect(startTimeInput).toHaveValue("09:30");
    expect(endTimeInput).toHaveValue("12:00");
  });
});
