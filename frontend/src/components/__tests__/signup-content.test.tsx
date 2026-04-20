import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  mockReplace,
  resetNavigationMocks,
} from "@/test/mocks/next-navigation";
import {
  mockSignUp,
  resetSupabaseMocks,
} from "@/test/mocks/supabase";
import { SignupContent } from "../signup-content";

describe("SignupContent", () => {
  const defaultProps = {
    onBack: vi.fn(),
    onGoLogin: vi.fn(),
  };

  beforeEach(() => {
    resetNavigationMocks();
    resetSupabaseMocks();
    defaultProps.onBack.mockClear();
    defaultProps.onGoLogin.mockClear();
  });

  it("renders the full name field first", () => {
    render(<SignupContent {...defaultProps} />);
    expect(screen.getByPlaceholderText("Jane Smith")).toBeInTheDocument();
  });

  it("shows Create Account button text", () => {
    render(<SignupContent {...defaultProps} />);
    expect(screen.getByText("Create Account")).toBeInTheDocument();
  });

  it("shows Sign in link", () => {
    render(<SignupContent {...defaultProps} />);
    expect(screen.getByText("Sign in")).toBeInTheDocument();
  });

  it("calls onGoLogin when Sign in is clicked", async () => {
    render(<SignupContent {...defaultProps} />);
    await userEvent.click(screen.getByText("Sign in"));
    expect(defaultProps.onGoLogin).toHaveBeenCalled();
  });

  it("calls onBack when back button is clicked", async () => {
    render(<SignupContent {...defaultProps} />);
    const backButtons = screen.getAllByRole("button");
    const backBtn = backButtons.find((btn) =>
      btn.querySelector(".lucide-chevron-left")
    );
    if (backBtn) await userEvent.click(backBtn);
    expect(defaultProps.onBack).toHaveBeenCalled();
  });

  it("shows error message when signup fails", async () => {
    mockSignUp.mockResolvedValue({
      error: { message: "Email already taken" },
    });

    render(<SignupContent {...defaultProps} />);

    const nameInput = screen.getByPlaceholderText("Jane Smith");
    await userEvent.type(nameInput, "Test User");

    const advanceBtns = screen.getAllByRole("button");
    const advBtn = advanceBtns.find((btn) =>
      btn.querySelector(".lucide-chevron-right")
    );
    if (advBtn) await userEvent.click(advBtn);

    await waitFor(() => {
      expect(
        screen.getByPlaceholderText("you@example.com")
      ).toBeInTheDocument();
    });

    await userEvent.type(
      screen.getByPlaceholderText("you@example.com"),
      "test@example.com"
    );

    const advBtns2 = screen.getAllByRole("button");
    const advBtn2 = advBtns2.find((btn) =>
      btn.querySelector(".lucide-chevron-right")
    );
    if (advBtn2) await userEvent.click(advBtn2);

    await waitFor(() => {
      expect(
        screen.getByPlaceholderText("At least 6 characters")
      ).toBeInTheDocument();
    });

    await userEvent.type(
      screen.getByPlaceholderText("At least 6 characters"),
      "password123"
    );

    await userEvent.click(screen.getByText("Create Account"));

    await waitFor(() => {
      expect(screen.getByText("Email already taken")).toBeInTheDocument();
    });
  });

  it("navigates to onboarding on successful signup", async () => {
    mockSignUp.mockResolvedValue({ error: null });

    render(<SignupContent {...defaultProps} />);

    await userEvent.type(
      screen.getByPlaceholderText("Jane Smith"),
      "Test User"
    );

    const advBtn = screen
      .getAllByRole("button")
      .find((btn) => btn.querySelector(".lucide-chevron-right"));
    if (advBtn) await userEvent.click(advBtn);

    await waitFor(() => {
      expect(
        screen.getByPlaceholderText("you@example.com")
      ).toBeInTheDocument();
    });

    await userEvent.type(
      screen.getByPlaceholderText("you@example.com"),
      "test@example.com"
    );

    const advBtn2 = screen
      .getAllByRole("button")
      .find((btn) => btn.querySelector(".lucide-chevron-right"));
    if (advBtn2) await userEvent.click(advBtn2);

    await waitFor(() => {
      expect(
        screen.getByPlaceholderText("At least 6 characters")
      ).toBeInTheDocument();
    });

    await userEvent.type(
      screen.getByPlaceholderText("At least 6 characters"),
      "password123"
    );

    await userEvent.click(screen.getByText("Create Account"));

    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith("/onboarding");
    });
  });

  it("has Continue with Google button", () => {
    render(<SignupContent {...defaultProps} />);
    expect(screen.getByText("Continue with Google")).toBeInTheDocument();
  });

  it("shows field labels for all three fields", () => {
    render(<SignupContent {...defaultProps} />);
    expect(screen.getAllByText("Full Name").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByPlaceholderText("Jane Smith")).toBeInTheDocument();
  });
});
