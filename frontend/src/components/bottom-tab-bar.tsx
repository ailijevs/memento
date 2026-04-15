"use client";

import { usePathname, useRouter } from "next/navigation";
import { BarChart3, CalendarDays, User } from "lucide-react";

const TABS = [
  { label: "Dashboard", href: "/dashboard", Icon: CalendarDays },
  { label: "Analytics", href: "/analytics", Icon: BarChart3 },
  { label: "Profile", href: "/profile", Icon: User },
];

export function BottomTabBar() {
  const pathname = usePathname();
  const router = useRouter();

  return (
    <div
      className="fixed bottom-0 left-1/2 -translate-x-1/2 w-full max-w-[430px] border-t border-white/[0.06]"
      style={{
        background: "oklch(0.04 0.005 270 / 92%)",
        backdropFilter: "blur(20px)",
        WebkitBackdropFilter: "blur(20px)",
        paddingBottom: "env(safe-area-inset-bottom)",
        zIndex: 50,
      }}
    >
      <div className="flex items-center">
        {TABS.map(({ label, href, Icon }) => {
          const isActive = pathname === href || pathname.startsWith(href + "/");
          return (
            <button
              key={href}
              onClick={() => router.push(href)}
              className="flex flex-1 flex-col items-center gap-1 py-3 transition-transform active:scale-95"
              style={{ color: isActive ? "rgba(255,255,255,0.95)" : "rgba(255,255,255,0.30)" }}
            >
              <Icon
                className="h-[22px] w-[22px]"
                strokeWidth={isActive ? 2 : 1.5}
              />
              <span className="text-[10px] font-medium tracking-[0.04em]">
                {label}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
