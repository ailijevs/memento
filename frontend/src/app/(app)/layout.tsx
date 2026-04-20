import { headers } from "next/headers";
import { redirect } from "next/navigation";
import { BottomTabBar } from "@/components/bottom-tab-bar";
import { safeNextPath } from "@/lib/internal-nav";
import { createClient } from "@/lib/supabase/server";

export default async function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    redirect("/login");
  }

  const isEmailProvider = user.app_metadata?.provider === "email";
  if (isEmailProvider && !user.email_confirmed_at) {
    redirect("/signup?verify=pending");
  }

  const termsAccepted = user.user_metadata?.terms_accepted === true;
  if (!termsAccepted) {
    const pathname = (await headers()).get("x-pathname") ?? "";
    const continuePath = safeNextPath(pathname, "/onboarding");
    const nextPath = continuePath === "/terms" ? "/onboarding" : continuePath;
    redirect(`/terms?next=${encodeURIComponent(nextPath)}`);
  }

  return (
    <>
      <div className="pb-20">{children}</div>
      <BottomTabBar />
    </>
  );
}
