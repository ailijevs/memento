"use client";

import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Loader2, Mail, Send, Users } from "lucide-react";
import { type EventResponse } from "@/lib/api";

interface HostMessageSheetContentProps {
  event: EventResponse;
  isSubmitting: boolean;
  onSubmit: (input: { subject: string; message: string }) => Promise<void>;
}

export function HostMessageSheetContent({
  event,
  isSubmitting,
  onSubmit,
}: HostMessageSheetContentProps) {
  const [subject, setSubject] = useState("");
  const [message, setMessage] = useState("");
  const [submitError, setSubmitError] = useState<string | null>(null);

  const defaultSubject = useMemo(() => `Update for ${event.name}`, [event.name]);

  useEffect(() => {
    setSubject(defaultSubject);
    setMessage("");
    setSubmitError(null);
  }, [defaultSubject, event.event_id]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitError(null);

    const trimmedSubject = subject.trim();
    const trimmedMessage = message.trim();

    if (!trimmedSubject || !trimmedMessage) {
      setSubmitError("Add both a subject and a message.");
      return;
    }

    try {
      await onSubmit({
        subject: trimmedSubject,
        message: trimmedMessage,
      });
    } catch (error) {
      if (error instanceof Error && error.message) {
        setSubmitError(error.message);
        return;
      }
      setSubmitError("Could not send your message right now. Please try again.");
    }
  }

  return (
    <form onSubmit={(event) => void handleSubmit(event)} className="min-h-0 flex flex-1 flex-col">
      <div className="min-h-0 flex-1 space-y-4 overflow-y-auto overscroll-contain pr-1 pb-4">
        <section
          className="rounded-3xl px-4 py-4"
          style={{
            background: "oklch(1 0 0 / 4%)",
            border: "1px solid oklch(1 0 0 / 10%)",
          }}
        >
          <div className="flex items-start gap-3">
            <div
              className="mt-0.5 rounded-2xl p-2"
              style={{
                background: "oklch(0.28 0.08 215 / 55%)",
                border: "1px solid oklch(0.62 0.14 215 / 22%)",
              }}
            >
              <Users className="h-4 w-4 text-white/85" />
            </div>
            <div>
              <p className="text-[15px] font-medium text-white/90">{event.name}</p>
              <p className="mt-1 text-[13px] leading-relaxed text-white/55">
                This email goes to members who have host messages enabled in their notification
                settings.
              </p>
            </div>
          </div>
        </section>

        <div>
          <label
            htmlFor="host-message-subject"
            className="mb-2 flex items-center gap-2 text-[11px] font-medium uppercase tracking-[0.08em] text-white/50"
          >
            <Mail className="h-3.5 w-3.5" />
            Subject
          </label>
          <input
            id="host-message-subject"
            value={subject}
            onChange={(event) => setSubject(event.target.value)}
            placeholder="Update for attendees"
            maxLength={160}
            className="h-10 w-full min-w-0 rounded-xl bg-transparent px-3 text-[16px] text-white outline-none placeholder:text-white/35"
            style={{
              background: "oklch(1 0 0 / 4%)",
              border: "1px solid oklch(1 0 0 / 10%)",
            }}
          />
        </div>

        <div>
          <label
            htmlFor="host-message-body"
            className="mb-2 flex items-center gap-2 text-[11px] font-medium uppercase tracking-[0.08em] text-white/50"
          >
            <Send className="h-3.5 w-3.5" />
            Message
          </label>
          <textarea
            id="host-message-body"
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            placeholder="Share an update with attendees..."
            rows={7}
            maxLength={5000}
            className="w-full min-w-0 resize-none rounded-2xl bg-transparent px-3 py-3 text-[16px] leading-relaxed text-white outline-none placeholder:text-white/35"
            style={{
              background: "oklch(1 0 0 / 4%)",
              border: "1px solid oklch(1 0 0 / 10%)",
            }}
          />
          <div className="mt-2 flex items-center justify-between text-[11px] text-white/38">
            <span>Keep it concise. Members receive this by email.</span>
            <span>{message.length}/5000</span>
          </div>
        </div>

        {submitError ? (
          <div
            className="rounded-2xl px-3 py-2 text-[12px] text-amber-200/90"
            style={{
              background: "oklch(0.3 0.09 70 / 22%)",
              border: "1px solid oklch(0.72 0.14 70 / 38%)",
            }}
          >
            {submitError}
          </div>
        ) : null}
      </div>

      <button
        type="submit"
        disabled={isSubmitting}
        className="mt-2 inline-flex h-11 items-center justify-center gap-2 rounded-2xl px-4 text-[13px] font-medium uppercase tracking-[0.08em] text-white transition-transform active:scale-[0.99] disabled:cursor-not-allowed disabled:opacity-55"
        style={{
          background: "linear-gradient(135deg, oklch(0.3 0.1 215) 0%, oklch(0.55 0.16 195) 100%)",
          border: "1px solid oklch(0.68 0.14 200 / 28%)",
        }}
      >
        {isSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
        {isSubmitting ? "Sending Message" : "Send to Members"}
      </button>
    </form>
  );
}
