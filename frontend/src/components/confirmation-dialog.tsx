"use client";

import { type ReactNode } from "react";

interface ConfirmationDialogProps {
  open: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  onConfirm: () => void;
  onCancel: () => void;
  confirmIcon?: ReactNode;
  confirmDisabled?: boolean;
  hideCancel?: boolean;
}

export function ConfirmationDialog({
  open,
  title,
  message,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  onConfirm,
  onCancel,
  confirmIcon,
  confirmDisabled = false,
  hideCancel = false,
}: ConfirmationDialogProps) {
  if (!open) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-[130] flex items-center justify-center px-6">
      <button
        aria-label="Close confirmation dialog"
        onClick={onCancel}
        className="absolute inset-0 h-full w-full"
        style={{ background: "rgba(0, 0, 0, 0.62)" }}
      />

      <div
        className="relative z-[131] w-full max-w-[380px] rounded-3xl p-4"
        style={{
          background: "oklch(0.12 0.02 265)",
          border: "1px solid oklch(1 0 0 / 12%)",
        }}
      >
        <h2 className="text-[18px] font-medium text-white/90">{title}</h2>
        <p className="mt-2 text-[13px] text-white/60">{message}</p>

        <div className="mt-4 flex gap-2">
          {!hideCancel ? (
            <button
              onClick={onCancel}
              className="flex-1 rounded-full px-3 py-2 text-[11px] font-medium uppercase tracking-[0.1em] text-white/75 transition-transform active:scale-95"
              style={{
                background: "oklch(1 0 0 / 4%)",
                border: "1px solid oklch(1 0 0 / 10%)",
              }}
            >
              {cancelLabel}
            </button>
          ) : null}
          <button
            onClick={onConfirm}
            disabled={confirmDisabled}
            className="flex flex-1 items-center justify-center gap-2 rounded-full px-3 py-2 text-[11px] font-medium uppercase tracking-[0.1em] text-white/85 transition-transform active:scale-95 disabled:opacity-55"
            style={{
              background: "oklch(0.22 0.11 25 / 62%)",
              border: "1px solid oklch(0.58 0.19 25 / 36%)",
            }}
          >
            {confirmIcon}
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
