import { useMemo, useState } from "react";
import { Clock, Loader2, Mountain, TrendingUp } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useTrails } from "@/features/trails/useTrails";
import { cn } from "@/lib/utils";
import type { Trail } from "@/types/api";

interface TrailsPanelProps {
  onSelect: (trail: Trail) => void;
}

function formatDuration(minutes: number): string {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return m ? `${h}h${m.toString().padStart(2, "0")}` : `${h}h`;
}

/** 1-5 difficulty as filled/empty dots — reads at a glance without a legend. */
function DifficultyDots({ level }: { level: number }) {
  return (
    <span className="flex gap-0.5" title={`Difficulty ${level}/5`}>
      {[1, 2, 3, 4, 5].map((i) => (
        <span
          key={i}
          className={cn(
            "h-1.5 w-1.5 rounded-full",
            i <= level ? "bg-green-700" : "bg-stone-200",
          )}
        />
      ))}
    </span>
  );
}

/**
 * Map overlay (top-left, under the search box): curated trail catalogue,
 * grouped by massif. Click a trail to fly to its trailhead.
 */
export function TrailsPanel({ onSelect }: TrailsPanelProps) {
  const [open, setOpen] = useState(false);
  const { data: trails, isLoading } = useTrails(open);

  const byRegion = useMemo(() => {
    const groups = new Map<string, Trail[]>();
    for (const t of trails ?? []) {
      groups.set(t.region, [...(groups.get(t.region) ?? []), t]);
    }
    return [...groups.entries()];
  }, [trails]);

  return (
    <div className="flex flex-col items-start gap-2">
      <Button
        size="sm"
        variant="outline"
        onClick={() => setOpen(!open)}
        className={cn(open && "bg-stone-100")}
      >
        <Mountain size={14} />
        Trails
      </Button>

      {open && (
        <div className="w-80 overflow-hidden rounded-lg border border-stone-200 bg-white shadow-xl">
          {isLoading && (
            <div className="flex h-20 items-center justify-center">
              <Loader2 size={16} className="animate-spin text-stone-400" />
            </div>
          )}
          {byRegion.length > 0 && (
            <div className="max-h-96 overflow-y-auto">
              {byRegion.map(([region, regionTrails]) => (
                <div key={region}>
                  <p className="sticky top-0 border-b border-stone-100 bg-stone-50 px-3 py-1 text-xs font-semibold uppercase tracking-wider text-stone-500">
                    {region}
                  </p>
                  <ul className="divide-y divide-stone-100">
                    {regionTrails.map((trail) => (
                      <li key={trail.id}>
                        <button
                          onClick={() => {
                            onSelect(trail);
                            setOpen(false);
                          }}
                          className="w-full px-3 py-2 text-left hover:bg-stone-50 transition-colors"
                        >
                          <div className="flex items-center justify-between gap-2">
                            <span className="text-sm font-medium text-stone-900">
                              {trail.name}
                            </span>
                            <DifficultyDots level={trail.difficulty} />
                          </div>
                          <div className="mt-0.5 flex gap-3 text-xs text-stone-500">
                            <span className="flex items-center gap-1">
                              <Clock size={11} /> {formatDuration(trail.duration_minutes)}
                            </span>
                            <span>{(trail.distance_m / 1000).toFixed(1)} km</span>
                            <span className="flex items-center gap-1">
                              <TrendingUp size={11} /> {trail.elevation_gain_m} m
                            </span>
                          </div>
                        </button>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
