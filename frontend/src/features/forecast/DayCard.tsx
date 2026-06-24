import { Wind, Droplets, Thermometer } from "lucide-react";
import { ScoreBadge, SCORE_DOT } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { DayForecast } from "@/types/api";

interface DayCardProps {
  day: DayForecast;
  isSelected?: boolean;
  onClick?: () => void;
}

const DAY_NAMES = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

function formatDate(dateStr: string): { dayName: string; dayNum: string } {
  const d = new Date(dateStr + "T12:00:00"); // noon to avoid timezone-shift issues
  return {
    dayName: DAY_NAMES[d.getDay()],
    dayNum: String(d.getDate()).padStart(2, "0"),
  };
}

export function DayCard({ day, isSelected, onClick }: DayCardProps) {
  const { dayName, dayNum } = formatDate(day.date);

  return (
    <button
      onClick={onClick}
      className={cn(
        "flex h-full w-44 shrink-0 flex-col gap-3 rounded-xl border p-3 text-left transition-all",
        "hover:border-sky-500/50 hover:bg-slate-700/60",
        isSelected
          ? "border-sky-500 bg-slate-700/80 ring-1 ring-sky-500/50"
          : "border-slate-700 bg-slate-800/80",
      )}
    >
      {/* Day header */}
      <div className="flex items-baseline justify-between">
        <div>
          <span className="text-xs font-semibold uppercase tracking-widest text-slate-400">
            {dayName}
          </span>
          <span className="ml-1.5 text-xs text-slate-500">{dayNum}</span>
        </div>
        <span
          className={cn("h-2 w-2 rounded-full", SCORE_DOT[day.verdict])}
          title={day.verdict}
        />
      </div>

      {/* Score badge */}
      <ScoreBadge verdict={day.verdict} score={day.score} className="w-full" />

      {/* Weather description */}
      <p className="text-xs leading-snug text-slate-400 line-clamp-2">
        {day.weather_description}
      </p>

      {/* Stats */}
      <div className="space-y-1">
        <div className="flex items-center gap-1.5 text-xs text-slate-400">
          <Thermometer size={12} className="shrink-0 text-amber-400" />
          <span>
            {Math.round(day.temp_max_c)}° / {Math.round(day.temp_min_c)}°C
          </span>
        </div>
        <div className="flex items-center gap-1.5 text-xs text-slate-400">
          <Wind size={12} className="shrink-0 text-sky-400" />
          <span>{Math.round(day.wind_gusts_max_kmh)} km/h gusts</span>
        </div>
        <div className="flex items-center gap-1.5 text-xs text-slate-400">
          <Droplets size={12} className="shrink-0 text-blue-400" />
          <span>{day.precipitation_sum_mm.toFixed(1)} mm</span>
        </div>
      </div>

      {/* Top reason (first in list, English) */}
      <p className="mt-auto text-xs italic leading-snug text-slate-500 line-clamp-2">
        {day.reasons_en[0] ?? "Good hiking conditions"}
      </p>
    </button>
  );
}
