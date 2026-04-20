import { createClient } from "@/lib/supabase/client";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * Signs out the user by:
 * 1. Revoking the session server-side via the backend
 * 2. Signing out of Supabase client-side
 * 3. Clearing all client-side storage (sessionStorage, localStorage onboarding state)
 */
export async function signOutUser(): Promise<void> {
  const supabase = createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();

  if (session?.access_token) {
    try {
      await fetch(`${API_URL}/api/v1/auth/signout`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${session.access_token}`,
          "Content-Type": "application/json",
        },
      });
    } catch {
      // Backend sign-out is best-effort; client-side cleanup still proceeds
    }
  }

  await supabase.auth.signOut();

  if (typeof window !== "undefined") {
    sessionStorage.clear();
    localStorage.removeItem("onboarding_missing_steps");
  }
}
