import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import type { ClimatologyResponse } from "@/types/api";

export function useClimatology(lat: number, lng: number) {
  return useQuery<ClimatologyResponse>({
    queryKey: ["climatology", lat, lng],
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
