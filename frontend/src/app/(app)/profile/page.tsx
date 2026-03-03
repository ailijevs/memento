"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { api, type ProfileResponse, type ProfileUpdateRequest } from "@/lib/api";
import { Aurora } from "@/components/aurora";
import {
  Camera,
  Check,
  X,
  Loader2,
  MapPin,
  Briefcase,
  GraduationCap,
  Pencil,
  LogOut,
} from "lucide-react";

export default function ProfilePage() {
  const router = useRouter();
  const [profile, setProfile] = useState<ProfileResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [editField, setEditField] = useState<string | null>(null);
  const [draftValue, setDraftValue] = useState("");
  const [saving, setSaving] = useState(false);
  const [photoLoading, setPhotoLoading] = useState(false);
  const [confirmingSignOut, setConfirmingSignOut] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  async function handleSignOut() {
    const supabase = createClient();
    await supabase.auth.signOut();
    router.push("/");
    router.refresh();
  }

  useEffect(() => {
    async function load() {
      const supabase = createClient();
      const {
        data: { session },
      } = await supabase.auth.getSession();
      if (!session) return;
      api.setToken(session.access_token);
      try {
        const p = await api.getProfile();
        setProfile(p);
      } finally {
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

  async function handlePhotoChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setPhotoLoading(true);
    try {
      const supabase = createClient();
      const {
        data: { session },
      } = await supabase.auth.getSession();
      if (!session) return;

      const filePath = `${session.user.id}/avatar.jpg`;
      await supabase.storage
        .from("profile-photos")
        .upload(filePath, file, { upsert: true, contentType: file.type });

      const {
        data: { publicUrl },
      } = supabase.storage.from("profile-photos").getPublicUrl(filePath);

      api.setToken(session.access_token);
      const updated = await api.updateProfile({ photo_path: publicUrl });
      setProfile(updated);
    } finally {
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
            {profile.photo_path ? (
              <img
                src={profile.photo_path}
                alt={profile.full_name}
                className="h-20 w-20 rounded-full object-cover"
                style={{ border: "1.5px solid rgba(255,255,255,0.15)" }}
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
                      {[edu.degree, edu.field_of_study]
                        .filter(Boolean)
                        .join(", ")}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </SectionCard>
        </div>

        {confirmingSignOut ? (
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
        ) : (
          <button
            onClick={() => setConfirmingSignOut(true)}
            className="mt-6 flex w-full items-center justify-center gap-2 py-2 text-[13px] text-white/25 active:text-white/50"
          >
            <LogOut className="h-3.5 w-3.5" />
            Sign Out
          </button>
        )}
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
