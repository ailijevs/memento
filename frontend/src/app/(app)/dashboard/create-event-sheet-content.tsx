"use client";

import { useMemo, useState } from "react";
import { Loader2 } from "lucide-react";

export interface CreateEventInput {
  name: string;
  starts_at?: string;
  ends_at?: string;
  location?: string;
}

interface CreateEventSheetContentProps {
  isSubmitting: boolean;
  onSubmit: (input: CreateEventInput) => Promise<void>;
}

export function CreateEventSheetContent({ isSubmitting, onSubmit }: CreateEventSheetContentProps) {
  const [name, setName] = useState("");
  const [startDate, setStartDate] = useState("");
  const [startTime, setStartTime] = useState("");
  const [endDate, setEndDate] = useState("");
  const [endTime, setEndTime] = useState("");
  const [location, setLocation] = useState("");
  const [error, setError] = useState<string | null>(null);

  const hasRequiredFields = useMemo(() => {
    return !(
      name.trim().length === 0 ||
      startDate.trim().length === 0 ||
      startTime.trim().length === 0 ||
      endDate.trim().length === 0 ||
      endTime.trim().length === 0
    );
  }, [endDate, endTime, name, startDate, startTime]);

  const hasValidDateOrder = useMemo(() => {
    if (!hasRequiredFields) {
      return true;
    }
    const startsAtDate = new Date(`${startDate}T${startTime}:00`);
    const endsAtDate = new Date(`${endDate}T${endTime}:00`);
    if (Number.isNaN(startsAtDate.getTime()) || Number.isNaN(endsAtDate.getTime())) {
      return false;
    }
    return endsAtDate > startsAtDate;
  }, [endDate, endTime, hasRequiredFields, startDate, startTime]);

  const isInvalid = !hasRequiredFields || !hasValidDateOrder;

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    const startsAtDate = new Date(`${startDate}T${startTime}:00`);
    const endsAtDate = new Date(`${endDate}T${endTime}:00`);

    if (Number.isNaN(startsAtDate.getTime()) || Number.isNaN(endsAtDate.getTime())) {
      setError("Please provide valid start and end times.");
      return;
    }

    if (endsAtDate <= startsAtDate) {
      setError("End time must be after start time.");
      return;
    }

    try {
      await onSubmit({
        name: name.trim(),
        starts_at: startsAtDate.toISOString(),
        ends_at: endsAtDate.toISOString(),
        location: location.trim() || undefined,
      });
      setName("");
      setStartDate("");
      setStartTime("");
      setEndDate("");
      setEndTime("");
      setLocation("");
    } catch (submitError) {
      const message = submitError instanceof Error ? submitError.message : "Failed to create event.";
      setError(message);
    }
  }

  return (
    <form
      onSubmit={(event) => void handleSubmit(event)}
      className="min-h-0 flex flex-1 flex-col overflow-x-hidden"
    >
      <div className="min-h-0 flex-1 space-y-3 overflow-y-auto overflow-x-hidden overscroll-contain pr-1 pb-4">
        <FieldLabel htmlFor="create-event-name" required>
          Event Name
        </FieldLabel>
        <input
          id="create-event-name"
          value={name}
          onChange={(event) => setName(event.target.value)}
          placeholder="Spring Networking Mixer"
          className="h-10 w-full min-w-0 max-w-full rounded-xl bg-transparent px-3 text-[16px] text-white outline-none placeholder:text-white/35"
          style={{
            background: "oklch(1 0 0 / 4%)",
            border: "1px solid oklch(1 0 0 / 10%)",
          }}
        />

        <FieldLabel htmlFor="create-event-location">Location</FieldLabel>
        <input
          id="create-event-location"
          value={location}
          onChange={(event) => setLocation(event.target.value)}
          placeholder="Austin Convention Center"
          className="h-10 w-full min-w-0 max-w-full rounded-xl bg-transparent px-3 text-[16px] text-white outline-none placeholder:text-white/35"
          style={{
            background: "oklch(1 0 0 / 4%)",
            border: "1px solid oklch(1 0 0 / 10%)",
          }}
        />

        <div className="grid grid-cols-[minmax(0,1.35fr)_minmax(0,1fr)] gap-2 overflow-hidden">
          <div className="min-w-0">
            <FieldLabel htmlFor="create-event-start-date" required>
              Start Date
            </FieldLabel>
            <PickerInput
              id="create-event-start-date"
              type="date"
              value={startDate}
              onChange={setStartDate}
              placeholder="Select date"
              displayValue={formatDateForDisplay(startDate)}
            />
          </div>
          <div className="min-w-0">
            <FieldLabel htmlFor="create-event-start-time" required>
              Start Time
            </FieldLabel>
            <PickerInput
              id="create-event-start-time"
              type="time"
              value={startTime}
              onChange={setStartTime}
              placeholder="Select time"
              displayValue={formatTimeForDisplay(startTime)}
            />
          </div>
        </div>

        <div className="grid grid-cols-[minmax(0,1.35fr)_minmax(0,1fr)] gap-2 overflow-hidden">
          <div className="min-w-0">
            <FieldLabel htmlFor="create-event-end-date" required>
              End Date
            </FieldLabel>
            <PickerInput
              id="create-event-end-date"
              type="date"
              value={endDate}
              onChange={setEndDate}
              placeholder="Select date"
              displayValue={formatDateForDisplay(endDate)}
            />
          </div>
          <div className="min-w-0">
            <FieldLabel htmlFor="create-event-end-time" required>
              End Time
            </FieldLabel>
            <PickerInput
              id="create-event-end-time"
              type="time"
              value={endTime}
              onChange={setEndTime}
              placeholder="Select time"
              displayValue={formatTimeForDisplay(endTime)}
            />
          </div>
        </div>

        {error ? <p className="text-[12px] text-red-300/90">{error}</p> : null}
        {!error && hasRequiredFields && !hasValidDateOrder ? (
          <p className="text-[12px] text-red-300/90">End time must be after start time.</p>
        ) : null}
        <div className="mt-2">
          <button
            type="submit"
            disabled={isInvalid || isSubmitting}
            className="inline-flex h-10 w-full items-center justify-center gap-2 rounded-full px-4 text-[12px] font-medium uppercase tracking-[0.1em] text-white transition-transform active:scale-[0.99] disabled:cursor-not-allowed disabled:opacity-55"
            style={{
              background: "oklch(0.23 0.1 35 / 62%)",
              border: "1px solid oklch(0.62 0.16 35 / 35%)",
            }}
          >
            {isSubmitting ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : null}
            {isSubmitting ? "Creating" : "Create Event"}
          </button>
        </div>
      </div>
    </form>
  );
}

interface FieldLabelProps {
  htmlFor: string;
  children: string;
  required?: boolean;
}

function FieldLabel({ htmlFor, children, required = false }: FieldLabelProps) {
  return (
    <label htmlFor={htmlFor} className="block text-[11px] font-medium uppercase tracking-[0.08em] text-white/55">
      {children}
      {required ? <span className="ml-1 text-red-300">*</span> : null}
    </label>
  );
}

interface PickerInputProps {
  id: string;
  type: "date" | "time";
  value: string;
  placeholder: string;
  displayValue: string;
  onChange: (value: string) => void;
}

function PickerInput({ id, type, value, placeholder, displayValue, onChange }: PickerInputProps) {
  return (
    <div
      className="relative h-10 w-full overflow-hidden rounded-xl px-2.5 text-[14px] text-white"
      style={{
        background: "oklch(1 0 0 / 4%)",
        border: "1px solid oklch(1 0 0 / 10%)",
      }}
    >
      <span className="pointer-events-none absolute inset-y-0 left-2.5 flex items-center truncate text-[14px] text-white/90">
        {displayValue || placeholder}
      </span>
      <input
        id={id}
        type={type}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="absolute inset-0 h-full w-full cursor-pointer appearance-none border-0 bg-transparent text-transparent opacity-0 outline-none"
        style={{ colorScheme: "dark" }}
      />
    </div>
  );
}

function formatDateForDisplay(value: string): string {
  if (!value) return "";
  const date = new Date(`${value}T00:00:00`);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric", year: "numeric" }).format(date);
}

function formatTimeForDisplay(value: string): string {
  if (!value) return "";
  const [hours, minutes] = value.split(":").map(Number);
  if (Number.isNaN(hours) || Number.isNaN(minutes)) return value;
  const date = new Date();
  date.setHours(hours, minutes, 0, 0);
  return new Intl.DateTimeFormat("en-US", { hour: "numeric", minute: "2-digit" }).format(date);
}
