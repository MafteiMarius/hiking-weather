import type { ScoreLabel } from "@/types/api";

// Soft tinted backgrounds with dark text — readable on a light UI without
// looking like traffic lights.
export const SCORE_STYLES: Record<ScoreLabel, string> = {
  Excellent: "bg-green-50 text-green-800 border-green-200",
  Good:      "bg-lime-50 text-lime-800 border-lime-200",
  Fair:      "bg-amber-50 text-amber-800 border-amber-200",
  Poor:      "bg-orange-50 text-orange-800 border-orange-200",
  Dangerous: "bg-red-50 text-red-800 border-red-200",
};

export const SCORE_DOT: Record<ScoreLabel, string> = {
  Excellent: "bg-green-600",
  Good:      "bg-lime-600",
  Fair:      "bg-amber-500",
  Poor:      "bg-orange-500",
  Dangerous: "bg-red-600",
};
