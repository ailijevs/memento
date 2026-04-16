import { vi } from "vitest";

export const mockSignInWithPassword = vi.fn();
export const mockSignUp = vi.fn();
export const mockSignInWithOAuth = vi.fn();
export const mockSignOut = vi.fn();
export const mockGetSession = vi.fn();
export const mockGetUser = vi.fn();

const mockAuth = {
  signInWithPassword: mockSignInWithPassword,
  signUp: mockSignUp,
  signInWithOAuth: mockSignInWithOAuth,
  signOut: mockSignOut,
  getSession: mockGetSession,
  getUser: mockGetUser,
  onAuthStateChange: vi.fn().mockReturnValue({
    data: { subscription: { unsubscribe: vi.fn() } },
  }),
};

vi.mock("@/lib/supabase/client", () => ({
  createClient: () => ({ auth: mockAuth }),
}));

export function resetSupabaseMocks() {
  mockSignInWithPassword.mockClear();
  mockSignUp.mockClear();
  mockSignInWithOAuth.mockClear();
  mockSignOut.mockClear();
  mockGetSession.mockClear();
  mockGetUser.mockClear();
}

export function mockSessionWith(accessToken = "fake-token") {
  mockGetSession.mockResolvedValue({
    data: {
      session: {
        access_token: accessToken,
        user: { id: "user-1", email: "test@example.com" },
      },
    },
  });
}

export function mockNoSession() {
  mockGetSession.mockResolvedValue({ data: { session: null } });
}
