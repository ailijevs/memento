"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import {
  api,
  type ProfileResponse,
  type ProfileCompletionResponse,
} from "@/lib/api";
import {
  Linkedin,
  Loader2,
  CheckCircle2,
  Circle,
  Briefcase,
  GraduationCap,
  MapPin,
  Sparkles,
} from "lucide-react";
import { Aurora } from "@/components/aurora";

type OnboardingStep = "linkedin" | "preview";

export default function OnboardingPage() {
  const router = useRouter();
  const [step, setStep] = useState<OnboardingStep>("linkedin");
  const [linkedinUrl, setLinkedinUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [profile, setProfile] = useState<ProfileResponse | null>(null);
  const [completion, setCompletion] =
    useState<ProfileCompletionResponse | null>(null);

  async function handleImport(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const supabase = createClient();
      const { data: { session } } = await supabase.auth.getSession();

      if (!session) {
        setError("Session expired. Please sign in again.");
        setLoading(false);
        return;
      }

      api.setToken(session.access_token);
      const result = await api.onboardFromLinkedIn(linkedinUrl);

      setProfile(result.profile);
      setCompletion(result.completion);
      setStep("preview");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to import profile");
    } finally {
      setLoading(false);
    }
  }

  if (step === "preview" && profile && completion) {
    return (
      <ProfilePreview
        profile={profile}
        completion={completion}
        onContinue={() => router.push("/dashboard")}
      />
    );
  }

  return (
    <div
      className="relative flex min-h-dvh flex-col px-6 overflow-hidden"
      style={{
        background: [
          "radial-gradient(ellipse 80% 50% at 50% 25%, oklch(0.09 0.05 275) 0%, transparent 100%)",
          "radial-gradient(ellipse 50% 40% at 70% 60%, oklch(0.07 0.03 240) 0%, transparent 100%)",
          "oklch(0.04 0.005 270)",
        ].join(", "),
      }}
    >
      <div className="absolute inset-0">
        <Aurora className="h-full w-full" mode="focused" />
      </div>

      {/* Content — centered */}
      <div className="relative z-10 my-auto w-full">
        <div className="animate-fade-up mb-10">
          <div className="mb-6 flex h-14 w-14 items-center justify-center rounded-[16px] bg-[#0A66C2]/15 ring-1 ring-[#0A66C2]/20">
            <Linkedin className="h-7 w-7 text-[#0A66C2]" />
          </div>
          <h1 className="text-large-title text-white">Import your profile</h1>
          <p className="text-callout mt-2 text-white/40">
            Paste your LinkedIn URL — we handle the rest
          </p>
        </div>

        <form onSubmit={handleImport} className="animate-fade-up delay-200 flex flex-col gap-5">
          <div>
            <label htmlFor="linkedin" className="mb-2 block text-footnote text-white/40">
              LinkedIn profile URL
            </label>
            <div className="relative">
              <Linkedin className="absolute left-4 top-1/2 h-[18px] w-[18px] -translate-y-1/2 text-white/20" />
              <input
                id="linkedin"
                type="url"
                placeholder="linkedin.com/in/yourname"
                value={linkedinUrl}
                onChange={(e) => setLinkedinUrl(e.target.value)}
                required
                className="h-[52px] w-full rounded-[14px] bg-white/[0.04] pl-12 pr-4 text-body text-white outline-none ring-1 ring-white/[0.06] transition-all placeholder:text-white/20 focus:bg-white/[0.06] focus:ring-white/[0.12]"
              />
            </div>
            <p className="mt-2 text-caption1 text-white/20">
              Name, headline, photo, experience, and education
            </p>
          </div>

          {error && <p className="text-footnote text-red-400/80">{error}</p>}

          <button
            type="submit"
            className="mt-2 flex h-[56px] w-full items-center justify-center gap-2.5 rounded-[16px] text-body font-semibold text-white/90 transition-all active:scale-[0.98] active:bg-white/[0.08]"
            style={{
              background: "oklch(1 0 0 / 5%)",
              boxShadow: "inset 0 0 0 1px oklch(0.5 0.15 275 / 20%), 0 0 30px oklch(0.4 0.12 275 / 12%)",
            }}
            disabled={loading}
          >
            {loading ? (
              <>
                <Loader2 className="h-5 w-5 animate-spin" />
                Importing...
              </>
            ) : (
              <>
                <Sparkles className="h-5 w-5" />
                Import Profile
              </>
            )}
          </button>
        </form>
      </div>
    </div>
  );
}

function ProfilePreview({
  profile,
  completion,
  onContinue,
}: {
  profile: ProfileResponse;
  completion: ProfileCompletionResponse;
  onContinue: () => void;
}) {
  return (
    <div
      className="relative flex min-h-dvh flex-col px-6 pt-12 pb-8 overflow-hidden"
      style={{
        background: [
          "radial-gradient(ellipse 80% 50% at 50% 25%, oklch(0.09 0.05 275) 0%, transparent 100%)",
          "radial-gradient(ellipse 50% 40% at 70% 60%, oklch(0.07 0.03 240) 0%, transparent 100%)",
          "oklch(0.04 0.005 270)",
        ].join(", "),
      }}
    >
      <div className="absolute inset-0">
        <Aurora className="h-full w-full" mode="focused" />
      </div>

      {/* Header */}
      <div className="animate-fade-up relative z-10 mb-8">
        <h1 className="text-large-title text-white">Looking good</h1>
        <p className="text-callout mt-2 text-white/40">
          This is how you&apos;ll appear to others
        </p>
      </div>

      {/* Scrollable content */}
      <div className="relative z-10 flex-1 overflow-y-auto">
        {/* Profile Card */}
        <div className="animate-scale-up delay-200 mb-5 rounded-[20px] bg-white/[0.04] p-6 ring-1 ring-white/[0.06]">
          <div className="flex items-start gap-4">
            {profile.photo_path ? (
              <img
                src={profile.photo_path}
                alt={profile.full_name}
                className="h-[72px] w-[72px] shrink-0 rounded-full object-cover ring-2 ring-white/[0.08]"
              />
            ) : (
              <div className="flex h-[72px] w-[72px] shrink-0 items-center justify-center rounded-full bg-white/[0.06] text-title1 text-white/40">
                {profile.full_name.charAt(0)}
              </div>
            )}
            <div className="min-w-0 pt-1">
              <h2 className="text-title3 truncate text-white">{profile.full_name}</h2>
              {profile.headline && (
                <p className="text-subhead mt-0.5 text-white/50 line-clamp-2">{profile.headline}</p>
              )}
              {profile.location && (
                <div className="text-caption1 mt-2 flex items-center gap-1.5 text-white/25">
                  <MapPin className="h-3 w-3" />
                  {profile.location}
                </div>
              )}
            </div>
          </div>

          {profile.bio && (
            <>
              <div className="my-5 h-px bg-white/[0.06]" />
              <p className="text-subhead leading-[1.6] text-white/40">{profile.bio}</p>
            </>
          )}

          {profile.experiences && profile.experiences.length > 0 && (
            <>
              <div className="my-5 h-px bg-white/[0.06]" />
              <div className="space-y-3">
                <h3 className="text-caption1 flex items-center gap-2 font-medium uppercase tracking-[0.1em] text-white/20">
                  <Briefcase className="h-3 w-3" />
                  Experience
                </h3>
                {profile.experiences.slice(0, 3).map((exp, i) => (
                  <div key={i}>
                    <p className="text-subhead font-medium text-white/70">{exp.title}</p>
                    <p className="text-footnote text-white/30">{exp.company}</p>
                  </div>
                ))}
              </div>
            </>
          )}

          {profile.education && profile.education.length > 0 && (
            <>
              <div className="my-5 h-px bg-white/[0.06]" />
              <div className="space-y-3">
                <h3 className="text-caption1 flex items-center gap-2 font-medium uppercase tracking-[0.1em] text-white/20">
                  <GraduationCap className="h-3 w-3" />
                  Education
                </h3>
                {profile.education.slice(0, 2).map((edu, i) => (
                  <div key={i}>
                    <p className="text-subhead font-medium text-white/70">{edu.school}</p>
                    <p className="text-footnote text-white/30">
                      {[edu.degree, edu.field_of_study].filter(Boolean).join(", ")}
                    </p>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>

        {/* Completion */}
        <div className="animate-fade-up delay-400 rounded-[20px] bg-white/[0.04] p-5 ring-1 ring-white/[0.06]">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="text-headline text-white/60">Completeness</h3>
            <span className="text-headline memento-gradient-text">
              {completion.completion_percentage}%
            </span>
          </div>

          <div className="mb-5 h-[5px] overflow-hidden rounded-full bg-white/[0.04]">
            <div
              className="memento-gradient h-full rounded-full transition-all duration-1000 ease-out"
              style={{
                width: `${completion.completion_percentage}%`,
                ...(completion.completion_percentage === 100
                  ? {
                      background:
                        "linear-gradient(90deg, oklch(0.6 0.18 155), oklch(0.65 0.15 165))",
                    }
                  : {}),
              }}
            />
          </div>

          <div className="grid grid-cols-2 gap-x-4 gap-y-3">
            {completion.filled_fields.map((field) => (
              <div key={field} className="text-footnote flex items-center gap-2 text-white/40">
                <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-400/70" />
                <span className="capitalize">{field.replace(/_/g, " ")}</span>
              </div>
            ))}
            {completion.missing_fields.map((field) => (
              <div key={field} className="text-footnote flex items-center gap-2 text-white/15">
                <Circle className="h-4 w-4 shrink-0" />
                <span className="capitalize">{field.replace(/_/g, " ")}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Bottom action */}
      <div className="animate-fade-up delay-600 relative z-10 pt-6">
        <button
          className="flex h-[56px] w-full items-center justify-center rounded-[16px] text-body font-semibold text-white/90 transition-all active:scale-[0.98] active:bg-white/[0.08]"
          style={{
            background: "oklch(1 0 0 / 5%)",
            boxShadow: "inset 0 0 0 1px oklch(0.5 0.15 275 / 20%), 0 0 30px oklch(0.4 0.12 275 / 12%)",
          }}
          onClick={onContinue}
        >
          Continue
        </button>
      </div>
    </div>
  );
}
