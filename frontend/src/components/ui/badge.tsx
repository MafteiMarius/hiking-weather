import { cn } from "@/lib/utils";
import type { Verdict } from "@/types/api";

const VERDICT_LABEL: Record<Verdict, string> = {
  go:      "Go",
  caution: "Caution",
  no_go:   "No Go",
};

const SCORE_STYLES: Record<Verdict, string> = {
  go:      "bg-green-500/20 text-green-400 border-green-500/30",
  caution: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
  no_go:   "bg-red-500/20 text-red-400 border-red-500/30",
};

export const SCORE_DOT: Record<Verdict, string> = {
  go:      "bg-green-400",
  caution: "bg-yellow-400",
  no_go:   "bg-red-400",
};

interface ScoreBadgeProps {
  verdict: Verdict;
  score: number;
  className?: string;
}

export function ScoreBadge({ verdict, score, className }: ScoreBadgeProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center rounded-xl border px-3 py-2",
        SCORE_STYLES[verdict],
        className,
      )}
    >
      <span className="text-2xl font-bold leading-none">{score}</span>
      <span className="mt-0.5 text-xs font-medium uppercase tracking-wide">
        {VERDICT_LABEL[verdict]}
      </span>
    </div>
  );
}
