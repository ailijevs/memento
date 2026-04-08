"use client";

import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { Aurora } from "@/components/aurora";
import { createClient } from "@/lib/supabase/client";

export default function TermsPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [accepting, setAccepting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const nextPath = searchParams.get("next") ?? "/dashboard";

  async function handleAccept() {
    setError(null);
    setAccepting(true);

    try {
      const supabase = createClient();
      const {
        data: { user },
        error: userError,
      } = await supabase.auth.getUser();

      if (userError || !user) {
        setError(userError?.message ?? "You need to be signed in to accept the terms.");
        setAccepting(false);
        return;
      }

      const { error: updateError } = await supabase.auth.updateUser({
        data: {
          terms_accepted: true,
          terms_accepted_at: new Date().toISOString(),
        },
      });

      if (updateError) {
        setError(updateError.message);
        setAccepting(false);
        return;
      }

      router.push(nextPath);
      router.refresh();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Something went wrong. Please try again.",
      );
      setAccepting(false);
    }
  }

  return (
    <div className="relative flex min-h-dvh flex-col overflow-hidden">
      <div className="absolute inset-0" style={{ opacity: 0.5 }}>
        <Aurora className="h-full w-full" mode="focused" />
      </div>

      <div className="relative z-10 mx-auto flex w-full max-w-xl flex-1 flex-col px-6 py-10">
        <h1
          className="mb-4 text-white"
          style={{
            fontFamily: "var(--font-serif)",
            fontSize: 28,
            fontWeight: 400,
            letterSpacing: "-0.02em",
          }}
        >
          Terms of Service
        </h1>

        <p className="mb-4 text-sm text-white/60">
          Please review and accept the terms of service before continuing to use Memento.
        </p>

        <div className="mb-4 flex-1 overflow-y-auto rounded-2xl border border-white/10 bg-black/40 p-4 text-sm text-white/70">
          <p className="mb-2 font-semibold">1. Usage at events</p>
          <p className="mb-4">
            Memento helps you recognize and remember people at supported events. Recognition is only
            available for events where you have joined and provided the necessary consents.
          </p>

          <p className="mb-2 font-semibold">2. Facial recognition and consent</p>
          <p className="mb-4">
            When enabled, Memento uses facial recognition to match faces captured by compatible devices
            to attendee profiles. You can withdraw consent for recognition in the app&apos;s event
            settings at any time, which will disable recognition for that event.
          </p>

          <p className="mb-2 font-semibold">3. Data storage and sharing</p>
          <p className="mb-4">
            Profile data (such as your name, headline, and shared interests) is stored in our backend
            and may be displayed to other attendees at the same event where you have granted
            permission. We do not sell your personal data.
          </p>

          <p className="mb-2 font-semibold">4. Your responsibilities</p>
          <p className="mb-4">
            You agree to use Memento in accordance with applicable laws and event codes of conduct. Do
            not attempt to misuse recognition features or circumvent consent mechanisms.
          </p>

          <p className="mb-2 font-semibold">5. Changes to these terms</p>
          <p>
            We may update these terms from time to time. When we do, we will notify you in the app and
            may ask you to accept updated terms before continuing to use recognition features.
          </p>
        </div>

        {error && <p className="mb-3 text-xs text-red-300">{error}</p>}

        <button
          type="button"
          onClick={handleAccept}
          disabled={accepting}
          className="mt-2 inline-flex items-center justify-center rounded-full bg-white px-6 py-2 text-[13px] font-medium text-black transition active:scale-95 disabled:opacity-60"
        >
          {accepting ? "Saving..." : "I have read and accept the terms"}
        </button>
      </div>
    </div>
  );
}

