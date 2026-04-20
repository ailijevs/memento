"use client";

import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Loader2 } from "lucide-react";

import { Aurora } from "@/components/aurora";
import { createClient } from "@/lib/supabase/client";

export default function TermsPage() {
  return (
    <Suspense
      fallback={
        <div className="relative flex min-h-dvh flex-col items-center justify-center overflow-hidden">
          <div className="absolute inset-0" style={{ opacity: 0.5 }}>
            <Aurora className="h-full w-full" mode="focused" />
          </div>
          <Loader2 className="relative z-10 h-6 w-6 animate-spin text-white/40" />
        </div>
      }
    >
      <TermsContent />
    </Suspense>
  );
}

function TermsContent() {
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
        setError(userError?.message ?? "You must be signed in to accept the terms.");
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
          Please review and accept these terms before continuing to use Memento.
        </p>

        <div className="mb-4 flex-1 overflow-y-auto rounded-2xl border border-white/10 bg-black/40 p-4 text-sm text-white/70">
          <p className="mb-2 font-semibold">1. Approved Event Use</p>
          <p className="mb-4">
            Memento is intended for use only at approved events where participants have
            registered and provided consent. Facial recognition features are limited to
            event-specific attendee groups and cannot be used outside those approved
            settings.
          </p>

          <p className="mb-2 font-semibold">2. Facial Recognition and Consent</p>
          <p className="mb-4">
            Memento uses facial recognition to match images captured by compatible devices
            with attendee profiles. Recognition is only available for users who have
            explicitly opted in. You may withdraw consent at any time through the app’s
            event settings. If consent is withdrawn, your profile and face data will no
            longer be available for recognition within that event.
          </p>

          <p className="mb-2 font-semibold">3. Data Collection and Storage</p>
          <p className="mb-4">
            Memento may store information you choose to provide, including your name,
            headline, academic or professional affiliation, interests, uploaded headshot,
            and event participation history. This information is stored securely and is only
            shared with other attendees in events where you have chosen to participate.
          </p>

          <p className="mb-2 font-semibold">4. Data Retention</p>
          <p className="mb-4">
            Event-specific facial recognition records and uploaded images may be deleted
            after the event period ends, unless you provide separate permission for longer
            retention. Memento does not sell personal data to advertisers or third parties.
          </p>

          <p className="mb-2 font-semibold">5. User Responsibilities</p>
          <p className="mb-4">
            You agree to use Memento in compliance with applicable laws, university
            policies, and event codes of conduct. You may not misuse facial recognition
            features, attempt to identify non-participants, share another person’s data
            without permission, or interfere with the system’s privacy protections.
          </p>

          <p className="mb-2 font-semibold">6. Accuracy and Availability</p>
          <p className="mb-4">
            Memento is designed to assist with networking and event interactions, but it
            may occasionally return incorrect, incomplete, or unavailable results.
            Recognition accuracy may vary depending on lighting, camera quality,
            connectivity, and the information provided by participants.
          </p>

          <p className="mb-2 font-semibold">7. Updates to These Terms</p>
          <p>
            We may update these terms from time to time to reflect product changes,
            privacy requirements, or legal obligations. If material changes are made, you
            will be notified in the app and may be required to accept the updated terms
            before continuing to use Memento.
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