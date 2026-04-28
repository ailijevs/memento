import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import { EventConsentsSheetContent } from "../event-consents-sheet-content";

const MOCK_CONSENT = {
  event_id: "evt-1",
  user_id: "user-1",
  allow_profile_display: true,
  allow_recognition: true,
  consented_at: "2026-01-01T00:00:00Z",
  revoked_at: null,
  updated_at: "2026-01-01T00:00:00Z",
};

describe("EventConsentsSheetContent", () => {
  it("shows loading spinner when loading", () => {
    render(
      <EventConsentsSheetContent
        loading={true}
        saving={false}
        consent={null}
        onToggleProfileDisplay={vi.fn()}
        onToggleRecognition={vi.fn()}
        onGrantAll={vi.fn()}
        onRevokeAll={vi.fn()}
      />,
    );

    const spinners = document.querySelectorAll(".animate-spin");
    expect(spinners.length).toBeGreaterThan(0);
  });

  it("shows error message when consent is null", () => {
    render(
      <EventConsentsSheetContent
        loading={false}
        saving={false}
        consent={null}
        onToggleProfileDisplay={vi.fn()}
        onToggleRecognition={vi.fn()}
        onGrantAll={vi.fn()}
        onRevokeAll={vi.fn()}
      />,
    );

    expect(screen.getByText("Could not load your event consent settings.")).toBeInTheDocument();
  });

  it("renders Profile Display and Face Recognition toggles", () => {
    render(
      <EventConsentsSheetContent
        loading={false}
        saving={false}
        consent={MOCK_CONSENT}
        onToggleProfileDisplay={vi.fn()}
        onToggleRecognition={vi.fn()}
        onGrantAll={vi.fn()}
        onRevokeAll={vi.fn()}
      />,
    );

    expect(screen.getByText("Profile Display")).toBeInTheDocument();
    expect(screen.getByText("Face Recognition")).toBeInTheDocument();
  });

  it("renders Grant All and Revoke All buttons", () => {
    render(
      <EventConsentsSheetContent
        loading={false}
        saving={false}
        consent={MOCK_CONSENT}
        onToggleProfileDisplay={vi.fn()}
        onToggleRecognition={vi.fn()}
        onGrantAll={vi.fn()}
        onRevokeAll={vi.fn()}
      />,
    );

    expect(screen.getByText("Grant All")).toBeInTheDocument();
    expect(screen.getByText("Revoke All")).toBeInTheDocument();
  });

  it("calls onToggleProfileDisplay when Profile Display toggle is clicked", async () => {
    const onToggleProfileDisplay = vi.fn();
    render(
      <EventConsentsSheetContent
        loading={false}
        saving={false}
        consent={MOCK_CONSENT}
        onToggleProfileDisplay={onToggleProfileDisplay}
        onToggleRecognition={vi.fn()}
        onGrantAll={vi.fn()}
        onRevokeAll={vi.fn()}
      />,
    );

    await userEvent.click(screen.getByLabelText("Profile Display"));
    expect(onToggleProfileDisplay).toHaveBeenCalledWith(false);
  });

  it("calls onToggleRecognition when Face Recognition toggle is clicked", async () => {
    const onToggleRecognition = vi.fn();
    render(
      <EventConsentsSheetContent
        loading={false}
        saving={false}
        consent={MOCK_CONSENT}
        onToggleProfileDisplay={vi.fn()}
        onToggleRecognition={onToggleRecognition}
        onGrantAll={vi.fn()}
        onRevokeAll={vi.fn()}
      />,
    );

    await userEvent.click(screen.getByLabelText("Face Recognition"));
    expect(onToggleRecognition).toHaveBeenCalledWith(false);
  });

  it("calls onGrantAll when Grant All is clicked", async () => {
    const consent = { ...MOCK_CONSENT, allow_profile_display: false, allow_recognition: false };
    const onGrantAll = vi.fn();
    render(
      <EventConsentsSheetContent
        loading={false}
        saving={false}
        consent={consent}
        onToggleProfileDisplay={vi.fn()}
        onToggleRecognition={vi.fn()}
        onGrantAll={onGrantAll}
        onRevokeAll={vi.fn()}
      />,
    );

    await userEvent.click(screen.getByText("Grant All"));
    expect(onGrantAll).toHaveBeenCalledOnce();
  });

  it("calls onRevokeAll when Revoke All is clicked", async () => {
    const onRevokeAll = vi.fn();
    render(
      <EventConsentsSheetContent
        loading={false}
        saving={false}
        consent={MOCK_CONSENT}
        onToggleProfileDisplay={vi.fn()}
        onToggleRecognition={vi.fn()}
        onGrantAll={vi.fn()}
        onRevokeAll={onRevokeAll}
      />,
    );

    await userEvent.click(screen.getByText("Revoke All"));
    expect(onRevokeAll).toHaveBeenCalledOnce();
  });

  it("disables Grant All when both consents are already on", () => {
    render(
      <EventConsentsSheetContent
        loading={false}
        saving={false}
        consent={MOCK_CONSENT}
        onToggleProfileDisplay={vi.fn()}
        onToggleRecognition={vi.fn()}
        onGrantAll={vi.fn()}
        onRevokeAll={vi.fn()}
      />,
    );

    expect(screen.getByText("Grant All").closest("button")).toBeDisabled();
  });

  it("disables Revoke All when both consents are already off", () => {
    const consent = { ...MOCK_CONSENT, allow_profile_display: false, allow_recognition: false };
    render(
      <EventConsentsSheetContent
        loading={false}
        saving={false}
        consent={consent}
        onToggleProfileDisplay={vi.fn()}
        onToggleRecognition={vi.fn()}
        onGrantAll={vi.fn()}
        onRevokeAll={vi.fn()}
      />,
    );

    expect(screen.getByText("Revoke All").closest("button")).toBeDisabled();
  });

  it("shows info text about consent usage", () => {
    render(
      <EventConsentsSheetContent
        loading={false}
        saving={false}
        consent={MOCK_CONSENT}
        onToggleProfileDisplay={vi.fn()}
        onToggleRecognition={vi.fn()}
        onGrantAll={vi.fn()}
        onRevokeAll={vi.fn()}
      />,
    );

    expect(
      screen.getByText("Update how this event can use your profile and face recognition data."),
    ).toBeInTheDocument();
  });
});
