import { useEffect } from "react";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";

interface DialogProps {
  open: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
  className?: string;
  /**
   * Visually hide the dialog WITHOUT unmounting it — unlike `open: false`,
   * the children (and their form state) stay alive. Used by flows that step
   * out to the map mid-edit, e.g. picking a home location in the profile.
   */
  hidden?: boolean;
}

export function Dialog({ open, onClose, title, children, className, hidden }: DialogProps) {
  // Close on Escape key — suspended while hidden so Escape can mean
  // "cancel the map interaction" instead of silently closing the dialog.
  useEffect(() => {
    if (!open || hidden) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [open, hidden, onClose]);

  if (!open) return null;

  return (
    <div
      className={cn(
        "fixed inset-0 z-[2000] flex items-center justify-center p-4",
        hidden && "hidden",
      )}
    >
      {/* Backdrop — z-[2000] clears Leaflet's highest layer (z ~700) */}
      <div
        className="absolute inset-0 bg-stone-900/40"
        onClick={onClose}
        aria-hidden
      />
      {/* Panel */}
      <div
        role="dialog"
        aria-modal
        aria-labelledby="dialog-title"
        className={cn(
          "relative z-10 w-full max-w-md rounded-2xl border border-stone-200",
          "bg-white shadow-2xl",
          className,
        )}
      >
        <div className="flex items-center justify-between border-b border-stone-200 px-6 py-4">
          <h2 id="dialog-title" className="text-lg font-semibold text-stone-900">
            {title}
          </h2>
          <button
            onClick={onClose}
            className="rounded-lg p-1 text-stone-400 hover:bg-stone-100 hover:text-stone-700 transition-colors"
            aria-label="Close"
          >
            <X size={18} />
          </button>
        </div>
        <div className="px-6 py-5">{children}</div>
      </div>
    </div>
  );
}
