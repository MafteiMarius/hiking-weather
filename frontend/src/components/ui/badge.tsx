import { cn } from "@/lib/utils";
import type { ScoreLabel } from "@/types/api";

const SCORE_STYLES: Record<ScoreLabel, string> = {
  Excellent: "bg-green-500/20 text-green-400 border-green-500/30",
  Good:      "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
  Fair:      "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
  Poor:      "bg-orange-500/20 text-orange-400 border-orange-500/30",
  Dangerous: "bg-red-500/20 text-red-400 border-red-500/30",
};

export const SCORE_DOT: Record<ScoreLabel, string> = {
  Excellent: "bg-green-400",
  Good:      "bg-emerald-400",
  Fair:      "bg-yellow-400",
  Poor:      "bg-orange-400",
  Dangerous: "bg-red-400",
};

interface ScoreBadgeProps {
  label: ScoreLabel;
  score: number;
  className?: string;
}

export function ScoreBadge({ label, score, className }: ScoreBadgeProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center rounded-xl border px-3 py-2",
        SCORE_STYLES[label],
        className,
      )}
    >
      <span className="text-2xl font-bold leading-none">{score}</span>
      <span className="mt-0.5 text-xs font-medium uppercase tracking-wide">{label}</span>
    </div>
  );
}
