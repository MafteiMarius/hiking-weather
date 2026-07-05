import { cn } from "@/lib/utils";
import { SCORE_STYLES } from "@/components/ui/score-colors";
import type { ScoreLabel } from "@/types/api";

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
