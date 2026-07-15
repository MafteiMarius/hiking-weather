import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import api from "@/lib/api";
import type { ForecastResponse, GeocodeResponse } from "@/types/api";

export function useForecast(lat: number, lng: number, enabled = true) {
  // Language is part of the key: the backend localizes weather descriptions and
  // score reasons, so ro and en are genuinely different payloads. Keying by it
  // means a toggle refetches (and caches both) instead of showing stale text.
  const { i18n } = useTranslation();
  return useQuery<ForecastResponse>({
    queryKey: ["forecast", lat, lng, i18n.language],
    queryFn: async () => {
      const { data } = await api.get<ForecastResponse>("/forecast", {
        params: { lat, lng, days: 7 },
      });
      return data;
    },
    enabled,
    staleTime: 1000 * 60 * 30, // respect the 30-min backend cache
  });
}

export function useGeocode(query: string) {
  return useQuery<GeocodeResponse>({
    queryKey: ["geocode", query],
    queryFn: async () => {
      const { data } = await api.get<GeocodeResponse>("/geocode", {
        params: { q: query },
      });
      return data;
    },
    enabled: query.length >= 2,
    staleTime: 1000 * 60 * 60, // geocode results don't change
  });
}
