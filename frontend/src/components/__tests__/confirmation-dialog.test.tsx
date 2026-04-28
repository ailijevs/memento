import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import { ConfirmationDialog } from "../confirmation-dialog";

describe("ConfirmationDialog", () => {
  const defaultProps = {
    open: true,
    title: "Delete item?",
    message: "This action cannot be undone.",
    onConfirm: vi.fn(),
    onCancel: vi.fn(),
  };

  it("renders nothing when open is false", () => {
    const { container } = render(
      <ConfirmationDialog {...defaultProps} open={false} />
    );
    expect(container.innerHTML).toBe("");
  });

  it("renders title and message when open", () => {
    render(<ConfirmationDialog {...defaultProps} />);
    expect(screen.getByText("Delete item?")).toBeInTheDocument();
    expect(screen.getByText("This action cannot be undone.")).toBeInTheDocument();
  });

  it("uses default button labels", () => {
    render(<ConfirmationDialog {...defaultProps} />);
    expect(screen.getByText("Cancel")).toBeInTheDocument();
    expect(screen.getByText("Confirm")).toBeInTheDocument();
  });

  it("uses custom button labels", () => {
    render(
      <ConfirmationDialog
        {...defaultProps}
        confirmLabel="Yes, delete"
        cancelLabel="Go back"
      />
    );
    expect(screen.getByText("Go back")).toBeInTheDocument();
    expect(screen.getByText("Yes, delete")).toBeInTheDocument();
  });

  it("calls onConfirm when confirm button is clicked", async () => {
    const onConfirm = vi.fn();
    render(<ConfirmationDialog {...defaultProps} onConfirm={onConfirm} />);
    await userEvent.click(screen.getByText("Confirm"));
    expect(onConfirm).toHaveBeenCalledTimes(1);
  });

  it("calls onCancel when cancel button is clicked", async () => {
    const onCancel = vi.fn();
    render(<ConfirmationDialog {...defaultProps} onCancel={onCancel} />);
    await userEvent.click(screen.getByText("Cancel"));
    expect(onCancel).toHaveBeenCalledTimes(1);
  });

  it("calls onCancel when backdrop is clicked", async () => {
    const onCancel = vi.fn();
    render(<ConfirmationDialog {...defaultProps} onCancel={onCancel} />);
    await userEvent.click(screen.getByLabelText("Close confirmation dialog"));
    expect(onCancel).toHaveBeenCalledTimes(1);
  });

  it("disables confirm button when confirmDisabled is true", () => {
    render(<ConfirmationDialog {...defaultProps} confirmDisabled />);
    const confirmBtn = screen.getByText("Confirm");
    expect(confirmBtn).toBeDisabled();
  });

  it("hides cancel button when hideCancel is true", () => {
    render(<ConfirmationDialog {...defaultProps} hideCancel />);
    expect(screen.queryByText("Cancel")).not.toBeInTheDocument();
    expect(screen.getByText("Confirm")).toBeInTheDocument();
  });

  it("renders confirm icon when provided", () => {
    render(
      <ConfirmationDialog
        {...defaultProps}
        confirmIcon={<span data-testid="icon">X</span>}
      />
    );
    expect(screen.getByTestId("icon")).toBeInTheDocument();
  });
});
