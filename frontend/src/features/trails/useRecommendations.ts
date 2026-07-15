import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import api from "@/lib/api";
import type { RecommendationResponse } from "@/types/api";

/**
 * Ranked trails for one forecast day. Only fetched while the panel is open
 * (enabled flag) — the backend hits Open-Meteo for every trail cell on a
 * cold cache, so we don't fire it speculatively.
 */
export function useRecommendations(date: string | undefined, enabled: boolean) {
  // Weather label/description/reason are localized server-side — key by language.
  const { i18n } = useTranslation();
  return useQuery<RecommendationResponse>({
    queryKey: ["recommendations", date, i18n.language],
    queryFn: async () => {
      const { data } = await api.get<RecommendationResponse>("/recommendations", {
        params: { date },
      });
      return data;
    },
    enabled: enabled && !!date,
    staleTime: 5 * 60 * 1000, // matches the mood of the 30-min forecast cache
    retry: false,
  });
}
