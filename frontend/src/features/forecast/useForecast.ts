import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import type { ForecastResponse, GeocodeResponse } from "@/types/api";

export function useForecast(lat: number, lng: number, enabled = true) {
  return useQuery<ForecastResponse>({
    queryKey: ["forecast", lat, lng],
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
