import { Wind, Droplets, Thermometer } from "lucide-react";
import { ScoreBadge } from "@/components/ui/badge";
import { SCORE_DOT } from "@/components/ui/score-colors";
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
        "hover:shadow-md",
        isSelected
          ? "border-green-600 bg-white shadow-md ring-1 ring-green-600/40"
          : "border-stone-200 bg-white shadow-sm",
      )}
    >
      {/* Day header */}
      <div className="flex items-baseline justify-between">
        <div>
          <span className="text-xs font-semibold uppercase tracking-widest text-stone-500">
            {dayName}
          </span>
          <span className="ml-1.5 text-xs text-stone-400">{dayNum}</span>
        </div>
        <span
          className={cn("h-2 w-2 rounded-full", SCORE_DOT[day.score_label])}
          title={day.score_label}
        />
      </div>

      {/* Score badge */}
      <ScoreBadge label={day.score_label} score={day.score} className="w-full" />

      {/* Weather description */}
      <p className="text-xs leading-snug text-stone-600 line-clamp-2">
        {day.weather_description}
      </p>

      {/* Stats */}
      <div className="space-y-1">
        <div className="flex items-center gap-1.5 text-xs text-stone-600">
          <Thermometer size={12} className="shrink-0 text-stone-400" />
          <span>
            {Math.round(day.temp_max_c)}° / {Math.round(day.temp_min_c)}°C
          </span>
        </div>
        <div className="flex items-center gap-1.5 text-xs text-stone-600">
          <Wind size={12} className="shrink-0 text-stone-400" />
          <span>{Math.round(day.wind_gusts_max_kmh)} km/h gusts</span>
        </div>
        <div className="flex items-center gap-1.5 text-xs text-stone-600">
          <Droplets size={12} className="shrink-0 text-stone-400" />
          <span>{day.precipitation_sum_mm.toFixed(1)} mm</span>
        </div>
      </div>

      {/* Score reason */}
      <p className="mt-auto text-xs italic leading-snug text-stone-500 line-clamp-2">
        {day.score_reason}
      </p>
    </button>
  );
}
