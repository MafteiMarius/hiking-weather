import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import api from "@/lib/api";
import type { ClimatologyResponse } from "@/types/api";

export function useClimatology(lat: number, lng: number) {
  // Instability sentences are localized server-side — see useForecast for why
  // the language belongs in the key.
  const { i18n } = useTranslation();
  return useQuery<ClimatologyResponse>({
    queryKey: ["climatology", lat, lng, i18n.language],
    queryFn: async () => {
      const { data } = await api.get<ClimatologyResponse>("/climatology", {
        params: { lat, lng },
      });
      return data;
    },
    // First hit for a new grid cell pulls 10 years of archive data (~1-3 s);
    // after that the backend serves its 30-day cache. Don't hammer on failure —
    // the banner is optional context, not core UI.
    retry: false,
    staleTime: 1000 * 60 * 60,
  });
}
