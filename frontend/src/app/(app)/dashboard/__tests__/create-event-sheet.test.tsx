import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import { CreateEventSheetContent } from "../create-event-sheet-content";

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
});
