"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";

interface ModalBottomSheetProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  children: ReactNode;
  maxHeight?: string;
}

const SHEET_ANIMATION_MS = 260;

export function ModalBottomSheet({
  isOpen,
  onClose,
  title,
  children,
  maxHeight = "86dvh",
}: ModalBottomSheetProps) {
  const [dragOffsetY, setDragOffsetY] = useState(0);
  const [isDragging, setIsDragging] = useState(false);
  const dragStartYRef = useRef<number | null>(null);

  useEffect(() => {
    if (!isOpen) {
      return;
    }

    const scrollY = window.scrollY;
    const previousOverflow = document.body.style.overflow;
    const previousPosition = document.body.style.position;
    const previousTop = document.body.style.top;
    const previousWidth = document.body.style.width;

    document.body.style.overflow = "hidden";
    document.body.style.position = "fixed";
    document.body.style.top = `-${scrollY}px`;
    document.body.style.width = "100%";

    return () => {
      document.body.style.overflow = previousOverflow;
      document.body.style.position = previousPosition;
      document.body.style.top = previousTop;
      document.body.style.width = previousWidth;
      window.scrollTo(0, scrollY);
    };
  }, [isOpen]);

  function handleSwipeStart(clientY: number) {
    if (!isOpen) {
      return;
    }
    setIsDragging(true);
    dragStartYRef.current = clientY;
    setDragOffsetY(0);
  }

  function handleSwipeMove(clientY: number) {
    if (dragStartYRef.current === null) {
      return;
    }
    const delta = clientY - dragStartYRef.current;
    setDragOffsetY(delta > 0 ? delta : 0);
  }

  function handleSwipeEnd() {
    if (dragOffsetY > 120) {
      setIsDragging(false);
      dragStartYRef.current = null;
      onClose();
      return;
    }

    setIsDragging(false);
    setDragOffsetY(0);
    dragStartYRef.current = null;
  }

  const translateY = isDragging ? `${dragOffsetY}px` : isOpen ? "0px" : "100%";

  return (
    <div
      className="fixed inset-0 z-[120] flex items-end justify-center"
      style={{ pointerEvents: isOpen ? "auto" : "none" }}
      aria-hidden={!isOpen}
    >
      <button
        onClick={onClose}
        className="absolute inset-0 h-full w-full transition-opacity duration-200"
        style={{
          background: "rgba(0, 0, 0, 0.64)",
          opacity: isOpen ? 1 : 0,
        }}
        aria-label="Close bottom sheet"
      />

      <div
        className="relative z-[121] w-full max-w-[430px] rounded-t-3xl border p-4 pb-6 shadow-2xl will-change-transform"
        style={{
          backgroundColor: "#10131a",
          borderColor: "rgba(255, 255, 255, 0.12)",
          maxHeight,
          transform: `translateY(${translateY})`,
          transition: isDragging ? "none" : `transform ${SHEET_ANIMATION_MS}ms cubic-bezier(0.22, 1, 0.36, 1)`,
        }}
      >
        <div
          className="mb-3 flex justify-center py-1"
          onTouchStart={(event) => handleSwipeStart(event.touches[0].clientY)}
          onTouchMove={(event) => {
            handleSwipeMove(event.touches[0].clientY);
            if (event.cancelable) {
              event.preventDefault();
            }
          }}
          onTouchEnd={handleSwipeEnd}
          onTouchCancel={handleSwipeEnd}
        >
          <div
            className="h-1.5 w-12 rounded-full"
            style={{ background: "rgba(255, 255, 255, 0.30)" }}
            aria-hidden="true"
          />
        </div>

        {title ? (
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-[18px] font-medium text-white/90">{title}</h2>
            <button
              onClick={onClose}
              className="rounded-full px-3 py-1.5 text-[11px] font-medium uppercase tracking-[0.08em] text-white/70"
              style={{
                background: "oklch(1 0 0 / 4%)",
                border: "1px solid oklch(1 0 0 / 10%)",
              }}
            >
              Close
            </button>
          </div>
        ) : null}

        {children}
      </div>
    </div>
  );
}
