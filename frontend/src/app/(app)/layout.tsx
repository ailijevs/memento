import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { BottomTabBar } from "@/components/bottom-tab-bar";

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

  return (
    <>
      <div className="pb-20">{children}</div>
      <BottomTabBar />
    </>
  );
}
