import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import { ModalBottomSheet } from "../modal-bottom-sheet";

describe("ModalBottomSheet", () => {
  const defaultProps = {
    isOpen: true,
    onClose: vi.fn(),
    children: <div>Sheet content</div>,
  };

  it("renders children when open", () => {
    render(<ModalBottomSheet {...defaultProps} />);
    expect(screen.getByText("Sheet content")).toBeInTheDocument();
  });

  it("has aria-hidden=true when closed", () => {
    const { container } = render(
      <ModalBottomSheet {...defaultProps} isOpen={false} />
    );
    const wrapper = container.firstChild as HTMLElement;
    expect(wrapper.getAttribute("aria-hidden")).toBe("true");
  });

  it("has aria-hidden=false when open", () => {
    const { container } = render(<ModalBottomSheet {...defaultProps} />);
    const wrapper = container.firstChild as HTMLElement;
    expect(wrapper.getAttribute("aria-hidden")).toBe("false");
  });

  it("renders title and close button when title is provided", () => {
    render(<ModalBottomSheet {...defaultProps} title="Settings" />);
    expect(screen.getByText("Settings")).toBeInTheDocument();
    expect(screen.getByText("Close")).toBeInTheDocument();
  });

  it("does not render title area when no title", () => {
    render(<ModalBottomSheet {...defaultProps} />);
    expect(screen.queryByText("Close")).not.toBeInTheDocument();
  });

  it("calls onClose when backdrop is clicked", async () => {
    const onClose = vi.fn();
    render(<ModalBottomSheet {...defaultProps} onClose={onClose} />);
    await userEvent.click(screen.getByLabelText("Close bottom sheet"));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("calls onClose when close button is clicked", async () => {
    const onClose = vi.fn();
    render(
      <ModalBottomSheet {...defaultProps} onClose={onClose} title="Test" />
    );
    await userEvent.click(screen.getByText("Close"));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("locks body scroll when open", () => {
    render(<ModalBottomSheet {...defaultProps} />);
    expect(document.body.style.overflow).toBe("hidden");
  });

  it("restores body scroll when closed", () => {
    const { rerender } = render(<ModalBottomSheet {...defaultProps} />);
    expect(document.body.style.overflow).toBe("hidden");
    rerender(<ModalBottomSheet {...defaultProps} isOpen={false} />);
    expect(document.body.style.overflow).not.toBe("hidden");
  });

  it("disables pointer events when closed", () => {
    const { container } = render(
      <ModalBottomSheet {...defaultProps} isOpen={false} />
    );
    const wrapper = container.firstChild as HTMLElement;
    expect(wrapper.style.pointerEvents).toBe("none");
  });
});
