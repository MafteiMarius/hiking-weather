import { isAxiosError } from "axios";
import { Home, Loader2, Sparkles } from "lucide-react";
import { Dialog } from "@/components/ui/dialog";
import { SCORE_STYLES } from "@/components/ui/score-colors";
import { useRecommendations } from "@/features/trails/useRecommendations";
import { cn } from "@/lib/utils";
import type { RecommendationItem, Trail } from "@/types/api";

interface RecommendPanelProps {
  date: string; // "2026-07-12" — the day being ranked
  open: boolean;
  onClose: () => void;
  onSelect: (trail: Trail) => void; // fly the map to the trailhead
}

function errorMessage(err: unknown): string {
  if (isAxiosError(err) && !err.response) return "Could not reach the server.";
  return "Could not rank the trails — try again in a moment.";
}

function PenaltyHint({ item }: { item: RecommendationItem }) {
  const parts: string[] = [];
  if (item.difficulty_penalty > 0) {
    parts.push(`−${item.difficulty_penalty} above your experience`);
  }
  if (item.distance_penalty > 0 && item.distance_from_home_km !== null) {
    parts.push(`−${item.distance_penalty} distance`);
  }
  if (parts.length === 0) return null;
  return <span className="text-xs text-stone-400">{parts.join(" · ")}</span>;
}

/**
 * Personalised "where to hike" list for the selected day: the weather safety
 * score at each trail's summit, adjusted by the user's profile (experience,
 * home distance). The breakdown is shown so the ranking never feels like a
 * black box.
 */
export function RecommendPanel({ date, open, onClose, onSelect }: RecommendPanelProps) {
  const recs = useRecommendations(date, open);

  if (!open) return null;

  const items = recs.data?.items ?? [];

  return (
    <Dialog open={open} onClose={onClose} title={`Best trails — ${date}`}>
      {recs.isPending && (
        <div className="flex flex-col items-center gap-3 py-8">
          <Loader2 size={24} className="animate-spin text-green-700" />
          <p className="text-sm text-stone-500">
            Checking the forecast on every summit…
          </p>
        </div>
      )}

      {recs.isError && (
        <p className="py-4 text-sm text-red-600">{errorMessage(recs.error)}</p>
      )}

      {recs.data && items.length === 0 && (
        <p className="py-4 text-sm text-stone-600">
          No trails match your profile filters for this day — try widening the
          distance or difficulty limits in your profile.
        </p>
      )}

      {items.length > 0 && (
        <div className="space-y-3">
          <ul className="divide-y divide-stone-100">
            {items.map((item, i) => (
              <li key={item.trail.id}>
                <button
                  onClick={() => {
                    onSelect(item.trail);
                    onClose();
                  }}
                  className="w-full py-2.5 text-left transition-colors hover:bg-stone-50"
                >
                  <div className="flex items-center gap-2">
                    <span className="w-5 shrink-0 text-right text-xs font-semibold text-stone-400">
                      {i + 1}.
                    </span>
                    <span className="min-w-0 flex-1 truncate text-sm font-medium text-stone-900">
                      {item.trail.name}
                    </span>
                    <span
                      className={cn(
                        "shrink-0 rounded border px-1.5 py-0.5 text-xs font-semibold",
                        SCORE_STYLES[item.weather_label],
                      )}
                      title={item.weather_reason}
                    >
                      {item.rank_score}
                    </span>
                  </div>
                  <div className="mt-0.5 flex flex-wrap items-center gap-x-3 gap-y-0.5 pl-7 text-xs text-stone-500">
                    <span>{item.trail.region}</span>
                    <span>{item.weather_description}</span>
                    <span>
                      {Math.round(item.temp_min_c)}°/{Math.round(item.temp_max_c)}°C
                    </span>
                    <span>{Math.round(item.wind_gusts_max_kmh)} km/h gusts</span>
                    {item.distance_from_home_km !== null && (
                      <span className="flex items-center gap-1">
                        <Home size={10} />
                        {Math.round(item.distance_from_home_km)} km
                      </span>
                    )}
                    <PenaltyHint item={item} />
                  </div>
                </button>
              </li>
            ))}
          </ul>

          <p className="flex items-center gap-1.5 text-xs text-stone-400">
            <Sparkles size={12} />
            Weather score at each summit, adjusted for your profile.
            {recs.data && recs.data.excluded > 0 && (
              <> {recs.data.excluded} trails hidden by your profile limits.</>
            )}
          </p>
        </div>
      )}
    </Dialog>
  );
}
