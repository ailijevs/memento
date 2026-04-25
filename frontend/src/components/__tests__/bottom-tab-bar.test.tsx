import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, beforeEach } from "vitest";
import {
  mockPush,
  mockPathname,
  resetNavigationMocks,
} from "@/test/mocks/next-navigation";
import { BottomTabBar } from "../bottom-tab-bar";

describe("BottomTabBar", () => {
  beforeEach(() => {
    resetNavigationMocks();
  });

  it("renders all tab labels", () => {
    render(<BottomTabBar />);
    expect(screen.getByText("Dashboard")).toBeInTheDocument();
    expect(screen.getByText("Profile")).toBeInTheDocument();
  });

  it("highlights the active tab based on pathname", () => {
    mockPathname.mockReturnValue("/dashboard");
    const { container } = render(<BottomTabBar />);
    const buttons = container.querySelectorAll("button");
    const dashboardBtn = buttons[0];
    const profileBtn = buttons[buttons.length - 1];
    expect(dashboardBtn.style.color).toContain("0.95");
    expect(profileBtn.style.color).toContain("0.3");
  });

  it("highlights Profile tab when on /profile path", () => {
    mockPathname.mockReturnValue("/profile");
    const { container } = render(<BottomTabBar />);
    const buttons = container.querySelectorAll("button");
    const profileBtn = buttons[buttons.length - 1];
    expect(profileBtn.style.color).toContain("0.95");
  });

  it("highlights tab for nested paths", () => {
    mockPathname.mockReturnValue("/dashboard/some-sub-page");
    const { container } = render(<BottomTabBar />);
    const buttons = container.querySelectorAll("button");
    const dashboardBtn = buttons[0];
    expect(dashboardBtn.style.color).toContain("0.95");
  });

  it("navigates when a tab is clicked", async () => {
    render(<BottomTabBar />);
    await userEvent.click(screen.getByText("Profile"));
    expect(mockPush).toHaveBeenCalledWith("/profile");
  });

  it("navigates to /dashboard when Dashboard tab is clicked", async () => {
    render(<BottomTabBar />);
    await userEvent.click(screen.getByText("Dashboard"));
    expect(mockPush).toHaveBeenCalledWith("/dashboard");
  });
});
