import { useEffect, useRef } from "react";
import { isAxiosError } from "axios";
import { Loader2, Sparkles, TriangleAlert } from "lucide-react";
import { Dialog } from "@/components/ui/dialog";
import { useEquipment } from "@/features/forecast/useEquipment";
import { cn } from "@/lib/utils";

interface PackingPanelProps {
  lat: number;
  lng: number;
  date: string; // "2026-07-05" — the selected day
  open: boolean;
  onClose: () => void;
}

function errorMessage(err: unknown): string {
  if (isAxiosError(err)) {
    if (err.response?.status === 503) {
      return "AI advice isn't configured on this server (no API key).";
    }
    if (!err.response) {
      return "Could not reach the server.";
    }
  }
  return "Could not get packing advice — try again in a moment.";
}

/**
 * AI packing advice for the selected day. The request fires when the dialog
 * opens (explicit user action — each call costs money server-side).
 */
export function PackingPanel({ lat, lng, date, open, onClose }: PackingPanelProps) {
  const equipment = useEquipment();
  const { mutate } = equipment;
  // Ref guard: StrictMode double-runs effects in dev, and each call costs
  // money — fire exactly once per mount (parent remounts us via key={date}).
  const fired = useRef(false);

  useEffect(() => {
    if (open && !fired.current) {
      fired.current = true;
      mutate({ lat, lng, date });
    }
  }, [open, lat, lng, date, mutate]);

  if (!open) return null;

  const plan = equipment.data;

  return (
    <Dialog open={open} onClose={onClose} title={`What to pack — ${date}`}>
      {equipment.isPending && (
        <div className="flex flex-col items-center gap-3 py-8">
          <Loader2 size={24} className="animate-spin text-green-700" />
          <p className="text-sm text-stone-500">
            Reading the forecast and putting a list together…
          </p>
        </div>
      )}

      {equipment.isError && (
        <div className="py-4">
          <p className="text-sm text-red-600">{errorMessage(equipment.error)}</p>
        </div>
      )}

      {plan && (
        <div className="space-y-4">
          <p className="text-sm leading-relaxed text-stone-700">{plan.summary}</p>

          {plan.warnings.length > 0 && (
            <div className="space-y-1 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2">
              {plan.warnings.map((w) => (
                <p key={w} className="flex items-start gap-2 text-xs text-amber-900">
                  <TriangleAlert size={13} className="mt-0.5 shrink-0 text-amber-600" />
                  {w}
                </p>
              ))}
            </div>
          )}

          <ul className="divide-y divide-stone-100">
            {plan.items.map((item) => (
              <li key={item.name} className="flex items-start gap-3 py-2">
                <span
                  className={cn(
                    "mt-0.5 shrink-0 rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase",
                    item.essential
                      ? "bg-green-50 text-green-800"
                      : "bg-stone-100 text-stone-500",
                  )}
                >
                  {item.essential ? "Essential" : "Optional"}
                </span>
                <span>
                  <span className="block text-sm font-medium text-stone-900">
                    {item.name}
                  </span>
                  <span className="block text-xs text-stone-500">{item.reason}</span>
                </span>
              </li>
            ))}
          </ul>

          <p className="flex items-center gap-1.5 text-xs text-stone-400">
            <Sparkles size={12} />
            AI-generated from the forecast — use your own judgement on the mountain.
          </p>
        </div>
      )}
    </Dialog>
  );
}
