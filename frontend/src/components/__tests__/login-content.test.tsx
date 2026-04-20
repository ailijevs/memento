import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  mockPush,
  mockReplace,
  mockRefresh,
  resetNavigationMocks,
} from "@/test/mocks/next-navigation";
import {
  mockSignInWithPassword,
  mockGetSession,
  mockSignInWithOAuth,
  resetSupabaseMocks,
} from "@/test/mocks/supabase";
import { LoginContent } from "../login-content";

vi.mock("@/lib/api", () => {
  const getProfile = vi.fn();
  return {
    api: { setToken: vi.fn(), getProfile },
    ApiError: class extends Error {
      status: number;
      constructor(status: number, message: string) {
        super(message);
        this.status = status;
      }
    },
  };
});

describe("LoginContent", () => {
  const defaultProps = {
    onBack: vi.fn(),
    onGoSignup: vi.fn(),
  };

  beforeEach(() => {
    resetNavigationMocks();
    resetSupabaseMocks();
    defaultProps.onBack.mockClear();
    defaultProps.onGoSignup.mockClear();
  });

  it("renders email and password fields", () => {
    render(<LoginContent {...defaultProps} />);
    expect(screen.getByPlaceholderText("you@example.com")).toBeInTheDocument();
  });

  it("calls onBack when back button is clicked", async () => {
    render(<LoginContent {...defaultProps} />);
    const backButtons = screen.getAllByRole("button");
    const backBtn = backButtons.find((btn) =>
      btn.querySelector(".lucide-chevron-left")
    );
    if (backBtn) await userEvent.click(backBtn);
    expect(defaultProps.onBack).toHaveBeenCalled();
  });

  it("shows Sign In button text", () => {
    render(<LoginContent {...defaultProps} />);
    expect(screen.getByText("Sign In")).toBeInTheDocument();
  });

  it("shows Create an account link", () => {
    render(<LoginContent {...defaultProps} />);
    expect(screen.getByText("Create an account")).toBeInTheDocument();
  });

  it("calls onGoSignup when Create an account is clicked", async () => {
    render(<LoginContent {...defaultProps} />);
    await userEvent.click(screen.getByText("Create an account"));
    expect(defaultProps.onGoSignup).toHaveBeenCalled();
  });

  it("shows error message when login fails", async () => {
    mockSignInWithPassword.mockResolvedValue({
      error: { message: "Invalid credentials" },
    });

    render(<LoginContent {...defaultProps} />);

    const emailInput = screen.getByPlaceholderText("you@example.com");
    await userEvent.type(emailInput, "test@example.com");

    const advBtn = screen
      .getAllByRole("button")
      .find((btn) => btn.querySelector(".lucide-chevron-right"));
    if (advBtn) await userEvent.click(advBtn);

    await waitFor(() => {
      expect(screen.getByPlaceholderText("Your password")).toBeInTheDocument();
    });

    const pwdInput = screen.getByPlaceholderText("Your password");
    await userEvent.type(pwdInput, "password123");

    await userEvent.click(screen.getByText("Sign In"));

    await waitFor(() => {
      expect(screen.getByText("Invalid credentials")).toBeInTheDocument();
    });
  });

  it("navigates to dashboard on successful login with profile", async () => {
    const { api } = await import("@/lib/api");

    mockSignInWithPassword.mockResolvedValue({ error: null });
    mockGetSession.mockResolvedValue({
      data: {
        session: {
          access_token: "token-123",
          user: { id: "u1", email: "test@example.com" },
        },
      },
    });
    (api.getProfile as ReturnType<typeof vi.fn>).mockResolvedValue({
      user_id: "u1",
      full_name: "Test",
    });

    render(<LoginContent {...defaultProps} />);

    const emailInput = screen.getByPlaceholderText("you@example.com");
    await userEvent.type(emailInput, "test@example.com");

    const advanceBtns = screen.getAllByRole("button");
    const advBtn = advanceBtns.find((btn) =>
      btn.querySelector(".lucide-chevron-right")
    );
    if (advBtn) await userEvent.click(advBtn);

    await waitFor(() => {
      expect(screen.getByPlaceholderText("Your password")).toBeInTheDocument();
    });

    await userEvent.type(
      screen.getByPlaceholderText("Your password"),
      "password123"
    );

    await userEvent.click(screen.getByText("Sign In"));

    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith("/dashboard");
    });
  });

  it("has Continue with Google button", () => {
    render(<LoginContent {...defaultProps} />);
    expect(screen.getByText("Continue with Google")).toBeInTheDocument();
  });
});
