"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import {
  ApiError,
  api,
  type NotificationPreferenceResponse,
  type ProfileResponse,
  type ProfileUpdateRequest,
} from "@/lib/api";
import { uploadProfilePhoto } from "@/lib/profile-photo-upload";
import { useProfilePhotoUrl } from "@/lib/use-profile-photo-url";
import { Aurora } from "@/components/aurora";
import { ConfirmationDialog } from "@/components/confirmation-dialog";
import {
  AlertTriangle,
  Bell,
  Camera,
  CalendarClock,
  Check,
  X,
  Loader2,
  Mail,
  MapPin,
  Briefcase,
  GraduationCap,
  MessageSquareText,
  Pencil,
  LogOut,
  Link2,
  Trash2,
} from "lucide-react";
import { signOutUser } from "@/lib/signout";

export default function ProfilePage() {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<"profile" | "settings">("profile");
  const [profile, setProfile] = useState<ProfileResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [editField, setEditField] = useState<string | null>(null);
  const [draftValue, setDraftValue] = useState("");
  const [saving, setSaving] = useState(false);
  const [photoLoading, setPhotoLoading] = useState(false);
  const [photoStatus, setPhotoStatus] = useState<string | null>(null);
  const [photoStatusError, setPhotoStatusError] = useState(false);
  const [confirmingSignOut, setConfirmingSignOut] = useState(false);
  const [deletePhase, setDeletePhase] = useState<"closed" | "first" | "second">("closed");
  const [deleteSubmitting, setDeleteSubmitting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [notificationPrefs, setNotificationPrefs] = useState<NotificationPreferenceResponse | null>(
    null
  );
  const [prefsLoading, setPrefsLoading] = useState(true);
  const [prefsSavingKey, setPrefsSavingKey] = useState<
    "email_notifications" | "event_updates" | "host_messages" | null
  >(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { photoUrl, handleImageError } = useProfilePhotoUrl(profile?.photo_path ?? null);

  async function handleSignOut() {
    await signOutUser();
    router.push("/");
    router.refresh();
  }

  const firstDeleteMessage =
    "Deleting your account will remove your profile, photos, and event participation from Memento. You'll be asked to confirm one more time before anything is removed.";
  const finalDeleteMessage =
    "If you continue, your event consents will be revoked automatically. You will no longer be able to access liked profiles or connections you have made. All of your data will be lost forever. This cannot be undone.";

  function closeDeleteDialog() {
    if (deleteSubmitting) return;
    setDeletePhase("closed");
    setDeleteError(null);
  }

  async function confirmDeleteAccount() {
    if (deleteSubmitting) return;
    setDeleteSubmitting(true);
    setDeleteError(null);
    try {
      await api.deleteMyAccount();
      const supabase = createClient();
      await supabase.auth.signOut();
      router.push("/");
      router.refresh();
    } catch (e) {
      setDeleteSubmitting(false);
      setDeleteError(
        e instanceof ApiError ? e.message : "Something went wrong. Please try again.",
      );
    }
  }

  useEffect(() => {
    async function load() {
      const supabase = createClient();
      const {
        data: { session },
      } = await supabase.auth.getSession();
      if (!session) {
        setLoading(false);
        return;
      }
      api.setToken(session.access_token);
      try {
        const [p, prefs] = await Promise.allSettled([
          api.getProfile(),
          api.getMyNotificationPreferences(),
        ]);
        if (p.status === "fulfilled") setProfile(p.value);
        if (prefs.status === "fulfilled") setNotificationPrefs(prefs.value);
      } finally {
        setPrefsLoading(false);
        setLoading(false);
      }
    }
    load();
  }, []);

  function startEdit(field: string, value: string) {
    setEditField(field);
    setDraftValue(value ?? "");
  }

  function cancelEdit() {
    setEditField(null);
    setDraftValue("");
  }

  async function saveEdit() {
    if (!profile || !editField) return;
    setSaving(true);
    try {
      const updated = await api.updateProfile({
        [editField]: draftValue,
      } as ProfileUpdateRequest);
      setProfile(updated);
      setEditField(null);
      setDraftValue("");
    } finally {
      setSaving(false);
    }
  }

  async function toggleNotificationPreference(
    key: "email_notifications" | "event_updates" | "host_messages"
  ) {
    if (!notificationPrefs || prefsSavingKey) return;
    const nextValue = !notificationPrefs[key];

    setPrefsSavingKey(key);
    const previous = notificationPrefs;
    setNotificationPrefs({ ...notificationPrefs, [key]: nextValue });

    try {
      const updated = await api.updateMyNotificationPreferences({ [key]: nextValue });
      setNotificationPrefs(updated);
    } catch {
      setNotificationPrefs(previous);
    } finally {
      setPrefsSavingKey(null);
    }
  }

  async function handlePhotoChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setPhotoLoading(true);
    setPhotoStatus("Uploading photo...");
    setPhotoStatusError(false);
    try {
      const supabase = createClient();
      const {
        data: { session },
      } = await supabase.auth.getSession();
      if (!session) return;

      api.setToken(session.access_token);
      const updated = await uploadProfilePhoto(file, "onboarding");
      setProfile(updated);
      setPhotoStatus("Upload complete.");
      setPhotoStatusError(false);
    } catch {
      setPhotoStatus("Upload failed. Please try again later.");
      setPhotoStatusError(true);
    } finally {
      e.target.value = "";
      setPhotoLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="flex min-h-dvh items-center justify-center">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-white/10 border-t-white/40" />
      </div>
    );
  }

  if (!profile) return null;

  const initials = profile.full_name
    ?.split(" ")
    .map((n) => n[0])
    .join("")
    .slice(0, 2)
    .toUpperCase() ?? "?";

  return (
    <div className="relative flex min-h-dvh flex-col overflow-hidden">
      {/* Aurora — subtle, only visible at the very top */}
      <div className="absolute inset-0" style={{ opacity: 0.38 }}>
        <Aurora className="h-full w-full" mode="ambient" />
      </div>
      <div
        className="pointer-events-none absolute inset-0"
        style={{
          background: [
            "linear-gradient(to bottom, transparent 0%, oklch(0.07 0.015 270) 35%)",
          ].join(", "),
        }}
      />

      {/* Scrollable content */}
      <div className="relative z-10 flex-1 overflow-y-auto px-6 pt-12 pb-6">
        {/* Avatar + name section */}
        <div className="mb-8 flex flex-col items-center">
          {/* Avatar */}
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            className="relative mb-4 transition-transform active:scale-95"
          >
            {photoUrl ? (
              <img
                src={photoUrl}
                alt={profile.full_name}
                className="h-20 w-20 rounded-full object-cover"
                style={{ border: "1.5px solid rgba(255,255,255,0.15)" }}
                onError={handleImageError}
              />
            ) : (
              <div
                className="flex h-20 w-20 items-center justify-center rounded-full text-[22px] font-light text-white/60"
                style={{
                  background: "rgba(255,255,255,0.06)",
                  border: "1.5px solid rgba(255,255,255,0.12)",
                }}
              >
                {initials}
              </div>
            )}
            <div
              className="absolute bottom-0 right-0 flex h-7 w-7 items-center justify-center rounded-full"
              style={{
                background: "rgba(255,255,255,0.10)",
                border: "1px solid rgba(255,255,255,0.14)",
              }}
            >
              {photoLoading ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin text-white/60" />
              ) : (
                <Camera className="h-3.5 w-3.5 text-white/60" />
              )}
            </div>
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            className="hidden"
            onChange={handlePhotoChange}
          />
          {photoStatus ? (
            <p
              className={`mt-1 text-[12px] ${
                photoStatusError ? "text-red-400/80" : "text-emerald-300/80"
              }`}
            >
              {photoStatus}
            </p>
          ) : null}

          {/* Name */}
          <FieldEditor
            field="full_name"
            value={profile.full_name}
            editField={editField}
            draftValue={draftValue}
            saving={saving}
            onStart={startEdit}
            onCancel={cancelEdit}
            onSave={saveEdit}
            onDraftChange={setDraftValue}
            placeholder="Your name"
            displayClassName="text-center text-white"
            displayStyle={{
              fontFamily: "var(--font-serif)",
              fontSize: 28,
              fontWeight: 400,
              letterSpacing: "-0.02em",
            }}
            inputClassName="w-full bg-transparent text-center text-white outline-none"
            inputStyle={{
              fontFamily: "var(--font-serif)",
              fontSize: 26,
              fontWeight: 400,
            }}
          />

          {/* Headline */}
          <FieldEditor
            field="headline"
            value={profile.headline ?? ""}
            editField={editField}
            draftValue={draftValue}
            saving={saving}
            onStart={startEdit}
            onCancel={cancelEdit}
            onSave={saveEdit}
            onDraftChange={setDraftValue}
            placeholder="Add a headline"
            displayClassName="mt-1 text-center text-[15px] text-white/50"
            inputClassName="w-full bg-transparent text-center text-[15px] text-white/80 outline-none"
          />
        </div>

        <div
          className="mb-4 flex w-full items-center gap-2 rounded-2xl p-1"
          style={{
            background: "rgba(255,255,255,0.06)",
            border: "1px solid rgba(255,255,255,0.12)",
          }}
        >
          <button
            type="button"
            onClick={() => setActiveTab("profile")}
            className="flex-1 rounded-xl px-3 py-2 text-[12px] font-medium transition-colors"
            style={{
              background:
                activeTab === "profile" ? "rgba(255,255,255,0.12)" : "transparent",
              color: activeTab === "profile" ? "rgba(255,255,255,0.92)" : "rgba(255,255,255,0.55)",
            }}
          >
            Profile Info
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("settings")}
            className="flex-1 rounded-xl px-3 py-2 text-[12px] font-medium transition-colors"
            style={{
              background:
                activeTab === "settings" ? "rgba(255,255,255,0.12)" : "transparent",
              color:
                activeTab === "settings" ? "rgba(255,255,255,0.92)" : "rgba(255,255,255,0.55)",
            }}
          >
            Account Settings
          </button>
        </div>

        {activeTab === "profile" ? (
          <div className="space-y-3">
            {/* About */}
            <SectionCard
              label="About"
              icon={null}
              onEdit={
                editField !== "bio"
                  ? () => startEdit("bio", profile.bio ?? "")
                  : undefined
              }
            >
              <FieldEditor
                field="bio"
                value={profile.bio ?? ""}
                editField={editField}
                draftValue={draftValue}
                saving={saving}
                onStart={startEdit}
                onCancel={cancelEdit}
                onSave={saveEdit}
                onDraftChange={setDraftValue}
                placeholder="Add a bio"
                multiline
                displayClassName="text-[14px] leading-relaxed text-white/60"
                inputClassName="w-full bg-transparent text-[14px] leading-relaxed text-white/80 outline-none resize-none"
                inputRows={4}
              />
            </SectionCard>

            {/* Location */}
            <SectionCard
              label="Location"
              icon={<MapPin className="h-3.5 w-3.5" />}
              onEdit={
                editField !== "location"
                  ? () => startEdit("location", profile.location ?? "")
                  : undefined
              }
            >
              <FieldEditor
                field="location"
                value={profile.location ?? ""}
                editField={editField}
                draftValue={draftValue}
                saving={saving}
                onStart={startEdit}
                onCancel={cancelEdit}
                onSave={saveEdit}
                onDraftChange={setDraftValue}
                placeholder="Add a location"
                displayClassName="text-[14px] text-white/60"
                inputClassName="w-full bg-transparent text-[14px] text-white/80 outline-none"
              />
            </SectionCard>

            {/* LinkedIn */}
            <SectionCard
              label="LinkedIn"
              icon={<Link2 className="h-3.5 w-3.5" />}
              onEdit={
                editField !== "linkedin_url"
                  ? () => startEdit("linkedin_url", profile.linkedin_url ?? "")
                  : undefined
              }
            >
              <FieldEditor
                field="linkedin_url"
                value={profile.linkedin_url ?? ""}
                editField={editField}
                draftValue={draftValue}
                saving={saving}
                onStart={startEdit}
                onCancel={cancelEdit}
                onSave={saveEdit}
                onDraftChange={setDraftValue}
                placeholder="Add a LinkedIn URL"
                displayClassName="text-[14px] text-white/60"
                inputClassName="w-full bg-transparent text-[14px] text-white/80 outline-none"
              />
            </SectionCard>

            {/* Work */}
            <SectionCard
              label="Work"
              icon={<Briefcase className="h-3.5 w-3.5" />}
              onEdit={
                editField !== "company"
                  ? () => startEdit("company", profile.company ?? "")
                  : undefined
              }
            >
              <FieldEditor
                field="company"
                value={profile.company ?? ""}
                editField={editField}
                draftValue={draftValue}
                saving={saving}
                onStart={startEdit}
                onCancel={cancelEdit}
                onSave={saveEdit}
                onDraftChange={setDraftValue}
                placeholder="Add a company"
                displayClassName="text-[14px] text-white/60"
                inputClassName="w-full bg-transparent text-[14px] text-white/80 outline-none"
              />
              {profile.experiences && profile.experiences.length > 0 && (
                <div className="mt-3 space-y-2.5 border-t border-white/[0.06] pt-3">
                  {profile.experiences.slice(0, 3).map((exp, i) => (
                    <div key={i}>
                      <p className="text-[13px] font-medium text-white/70">
                        {exp.title}
                      </p>
                      <p className="text-[12px] text-white/40">
                        {exp.company}
                        {exp.start_date &&
                          ` · ${exp.start_date}${exp.end_date ? ` – ${exp.end_date}` : " – Present"}`}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </SectionCard>

            {/* Education */}
            <SectionCard
              label="Education"
              icon={<GraduationCap className="h-3.5 w-3.5" />}
              onEdit={
                editField !== "major"
                  ? () => startEdit("major", profile.major ?? "")
                  : undefined
              }
            >
              <FieldEditor
                field="major"
                value={profile.major ?? ""}
                editField={editField}
                draftValue={draftValue}
                saving={saving}
                onStart={startEdit}
                onCancel={cancelEdit}
                onSave={saveEdit}
                onDraftChange={setDraftValue}
                placeholder="Add a major"
                displayClassName="text-[14px] text-white/60"
                inputClassName="w-full bg-transparent text-[14px] text-white/80 outline-none"
              />
              {profile.education && profile.education.length > 0 && (
                <div className="mt-3 space-y-2.5 border-t border-white/[0.06] pt-3">
                  {profile.education.slice(0, 2).map((edu, i) => (
                    <div key={i}>
                      <p className="text-[13px] font-medium text-white/70">
                        {edu.school}
                      </p>
                      <p className="text-[12px] text-white/40">
                        {[edu.degree, edu.field_of_study].filter(Boolean).join(", ")}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </SectionCard>
          </div>
        ) : (
          <div className="space-y-3">
            <SectionCard label="Account Settings" icon={<Bell className="h-3.5 w-3.5" />}>
              {prefsLoading ? (
                <div className="flex items-center justify-center py-3">
                  <Loader2 className="h-4 w-4 animate-spin text-white/45" />
                </div>
              ) : !notificationPrefs ? (
                <p className="text-[12px] text-white/45">
                  Could not load notification settings.
                </p>
              ) : (
                <div className="space-y-2">
                  <PreferenceToggleRow
                    icon={<Mail className="h-3.5 w-3.5" />}
                    title="Email Notifications"
                    description="Master toggle for all email updates."
                    enabled={notificationPrefs.email_notifications}
                    disabled={Boolean(prefsSavingKey)}
                    onToggle={() => toggleNotificationPreference("email_notifications")}
                  />
                  <PreferenceToggleRow
                    icon={<CalendarClock className="h-3.5 w-3.5" />}
                    title="Event Updates"
                    description="Email me when event details change."
                    enabled={notificationPrefs.event_updates}
                    disabled={Boolean(prefsSavingKey)}
                    onToggle={() => toggleNotificationPreference("event_updates")}
                  />
                  <PreferenceToggleRow
                    icon={<MessageSquareText className="h-3.5 w-3.5" />}
                    title="Host Messages"
                    description="Email me announcements from event hosts."
                    enabled={notificationPrefs.host_messages}
                    disabled={Boolean(prefsSavingKey)}
                    onToggle={() => toggleNotificationPreference("host_messages")}
                  />
                </div>
              )}
            </SectionCard>
          </div>
        )}

        {activeTab === "settings" && confirmingSignOut ? (
          <div className="mt-6 flex items-center justify-center gap-3">
            <span className="text-[13px] text-white/40">Sign out?</span>
            <button
              onClick={handleSignOut}
              className="rounded-full px-4 py-1.5 text-[12px] font-medium text-red-400/80 active:text-red-400"
              style={{ background: "rgba(255,80,80,0.08)", border: "1px solid rgba(255,80,80,0.15)" }}
            >
              Yes, sign out
            </button>
            <button
              onClick={() => setConfirmingSignOut(false)}
              className="text-[12px] text-white/25 active:text-white/50"
            >
              Cancel
            </button>
          </div>
        ) : activeTab === "settings" ? (
          <button
            onClick={() => setConfirmingSignOut(true)}
            className="mt-6 flex w-full items-center justify-center gap-2 py-2 text-[13px] text-white/25 active:text-white/50"
          >
            <LogOut className="h-3.5 w-3.5" />
            Sign Out
          </button>
        ) : null}

        {activeTab === "settings" && (
          <div
            className="mt-10 rounded-2xl p-4"
            style={{
              background: "rgba(255, 60, 60, 0.08)",
              border: "2px solid rgba(255, 100, 100, 0.45)",
              boxShadow: "0 0 24px rgba(255, 60, 60, 0.12)",
            }}
          >
            <div className="mb-3 flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 shrink-0 text-red-400" aria-hidden />
              <span className="text-[13px] font-semibold uppercase tracking-[0.12em] text-red-200/90">
                Danger zone
              </span>
            </div>
            <p className="mb-4 text-[13px] leading-relaxed text-red-100/75">
              Permanently delete your Memento account and all associated data. This action cannot be
              undone.
            </p>
            <button
              type="button"
              onClick={() => {
                setDeleteError(null);
                setDeleteSubmitting(false);
                setDeletePhase("first");
              }}
              className="flex w-full items-center justify-center gap-2 rounded-xl px-4 py-3.5 text-[14px] font-semibold text-white transition-transform active:scale-[0.99]"
              style={{
                background: "linear-gradient(180deg, oklch(0.52 0.22 25) 0%, oklch(0.4 0.2 22) 100%)",
                border: "1px solid oklch(0.65 0.2 25 / 55%)",
                boxShadow: "0 4px 20px rgba(220, 38, 38, 0.35)",
              }}
            >
              <Trash2 className="h-5 w-5" aria-hidden />
              Delete my account
            </button>
          </div>
        )}

        <ConfirmationDialog
          open={deletePhase === "first"}
          title="Delete your account?"
          message={firstDeleteMessage}
          cancelLabel="Cancel"
          confirmLabel="Continue"
          onCancel={closeDeleteDialog}
          onConfirm={() => {
            setDeleteError(null);
            setDeletePhase("second");
          }}
        />

        <ConfirmationDialog
          open={deletePhase === "second"}
          title="Are you sure?"
          message={
            deleteError
              ? `${finalDeleteMessage}\n\n${deleteError}`
              : finalDeleteMessage
          }
          cancelLabel="Cancel"
          confirmLabel={deleteSubmitting ? "Deleting…" : "Yes, delete my account"}
          confirmDisabled={deleteSubmitting}
          onCancel={closeDeleteDialog}
          onConfirm={() => void confirmDeleteAccount()}
          confirmIcon={
            deleteSubmitting ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden />
            ) : undefined
          }
        />
      </div>
    </div>
  );
}

function PreferenceToggleRow({
  icon,
  title,
  description,
  enabled,
  disabled,
  onToggle,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
  enabled: boolean;
  disabled: boolean;
  onToggle: () => void;
}) {
  return (
    <div
      className="rounded-xl px-3 py-2.5"
      style={{
        background: "rgba(255,255,255,0.04)",
        border: "1px solid rgba(255,255,255,0.08)",
      }}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-1.5 text-white/75">
            {icon}
            <p className="text-[13px] font-medium">{title}</p>
          </div>
          <p className="mt-1 text-[11px] leading-relaxed text-white/45">{description}</p>
        </div>
        <button
          type="button"
          role="switch"
          aria-checked={enabled}
          aria-label={title}
          disabled={disabled}
          onClick={onToggle}
          className="relative inline-flex h-6 w-11 shrink-0 rounded-full transition-colors disabled:opacity-55"
          style={{
            background: enabled ? "oklch(0.59 0.18 160 / 90%)" : "oklch(1 0 0 / 18%)",
            border: enabled
              ? "1px solid oklch(0.72 0.14 160 / 58%)"
              : "1px solid oklch(1 0 0 / 20%)",
          }}
        >
          <span
            className="absolute top-[1px] h-[20px] w-[20px] rounded-full bg-white transition-transform"
            style={{
              transform: enabled ? "translateX(21px)" : "translateX(1px)",
            }}
          />
        </button>
      </div>
    </div>
  );
}

// ─── Section card wrapper ─────────────────────────────────────────────────────

function SectionCard({
  label,
  icon,
  children,
  onEdit,
}: {
  label: string;
  icon: React.ReactNode;
  children: React.ReactNode;
  onEdit?: () => void;
}) {
  return (
    <div
      className="rounded-2xl px-4 py-4"
      style={{
        background: "rgba(255,255,255,0.07)",
        border: "1px solid rgba(255,255,255,0.12)",
      }}
    >
      <div className="mb-2.5 flex items-center justify-between">
        <div className="flex items-center gap-1.5 text-white/35">
          {icon}
          <span className="text-[10px] font-semibold uppercase tracking-[0.14em]">
            {label}
          </span>
        </div>
        {onEdit && (
          <button
            onClick={onEdit}
            className="flex h-6 w-6 items-center justify-center rounded-full text-white/30 transition-colors active:text-white/60"
            style={{
              background: "rgba(255,255,255,0.04)",
              border: "1px solid rgba(255,255,255,0.08)",
            }}
          >
            <Pencil className="h-3 w-3" />
          </button>
        )}
      </div>
      {children}
    </div>
  );
}

// ─── Inline editable field ────────────────────────────────────────────────────

function FieldEditor({
  field,
  value,
  editField,
  draftValue,
  saving,
  onStart,
  onCancel,
  onSave,
  onDraftChange,
  placeholder,
  multiline,
  displayClassName,
  displayStyle,
  inputClassName,
  inputStyle,
  inputRows,
}: {
  field: string;
  value: string;
  editField: string | null;
  draftValue: string;
  saving: boolean;
  onStart: (field: string, value: string) => void;
  onCancel: () => void;
  onSave: () => void;
  onDraftChange: (v: string) => void;
  placeholder?: string;
  multiline?: boolean;
  displayClassName?: string;
  displayStyle?: React.CSSProperties;
  inputClassName?: string;
  inputStyle?: React.CSSProperties;
  inputRows?: number;
}) {
  const isEditing = editField === field;

  if (isEditing) {
    return (
      <div className="flex items-start gap-2">
        {multiline ? (
          <textarea
            value={draftValue}
            onChange={(e) => onDraftChange(e.target.value)}
            className={inputClassName}
            style={inputStyle}
            rows={inputRows ?? 3}
            autoFocus
            placeholder={placeholder}
          />
        ) : (
          <input
            type="text"
            value={draftValue}
            onChange={(e) => onDraftChange(e.target.value)}
            className={inputClassName}
            style={inputStyle}
            autoFocus
            placeholder={placeholder}
            onKeyDown={(e) => {
              if (e.key === "Enter") onSave();
              if (e.key === "Escape") onCancel();
            }}
          />
        )}
        <div className="flex shrink-0 items-center gap-1">
          <button
            onClick={onSave}
            disabled={saving}
            className="flex h-7 w-7 items-center justify-center rounded-full text-white/60 active:text-white transition-colors"
            style={{
              background: "rgba(255,255,255,0.06)",
              border: "1px solid rgba(255,255,255,0.12)",
            }}
          >
            {saving ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Check className="h-3.5 w-3.5" />
            )}
          </button>
          <button
            onClick={onCancel}
            className="flex h-7 w-7 items-center justify-center rounded-full text-white/30 active:text-white/60 transition-colors"
            style={{
              background: "rgba(255,255,255,0.03)",
              border: "1px solid rgba(255,255,255,0.08)",
            }}
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>
    );
  }

  return (
    <button
      type="button"
      onClick={() => onStart(field, value)}
      className={`w-full text-left ${displayClassName ?? ""}`}
      style={displayStyle}
    >
      {value || (
        <span style={{ opacity: 0.22 }}>{placeholder ?? "Tap to edit"}</span>
      )}
    </button>
  );
}
