import { TriangleAlert } from "lucide-react";
import { useClimatology } from "@/features/forecast/useClimatology";

interface InstabilityBannerProps {
  lat: number;
  lng: number;
}

/**
 * Historical instability warning — shown only when the location has a track
 * record of trouble for this week of the year, even if the forecast is fine.
 * Silent on loading and on error: this is context, not core UI.
 */
export function InstabilityBanner({ lat, lng }: InstabilityBannerProps) {
  const { data } = useClimatology(lat, lng);

  if (!data?.unstable) return null;

  return (
    <div className="flex items-start gap-2 border-b border-amber-200 bg-amber-50 px-4 py-2">
      <TriangleAlert size={14} className="mt-0.5 shrink-0 text-amber-600" />
      <div className="text-xs leading-snug text-amber-900">
        <span className="font-semibold">
          Historically unstable this week of the year.
        </span>{" "}
        {data.reasons.join(". ")}.
      </div>
    </div>
  );
}
