import { vi } from "vitest";

export const mockPush = vi.fn();
export const mockReplace = vi.fn();
export const mockBack = vi.fn();
export const mockRefresh = vi.fn();
export const mockPathname = vi.fn().mockReturnValue("/dashboard");
export const mockSearchParams = new URLSearchParams();

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: mockPush,
    replace: mockReplace,
    back: mockBack,
    refresh: mockRefresh,
    prefetch: vi.fn(),
  }),
  usePathname: () => mockPathname(),
  useParams: () => ({}),
  useSearchParams: () => mockSearchParams,
}));

export function resetNavigationMocks() {
  mockPush.mockClear();
  mockReplace.mockClear();
  mockBack.mockClear();
  mockRefresh.mockClear();
  mockPathname.mockReturnValue("/dashboard");
}
