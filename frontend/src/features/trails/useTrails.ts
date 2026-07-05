import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import type { Trail } from "@/types/api";

export function useTrails(enabled: boolean) {
  return useQuery<Trail[]>({
    queryKey: ["trails"],
    queryFn: async () => {
      const { data } = await api.get<Trail[]>("/trails");
      return data;
    },
    enabled, // fetched lazily when the panel first opens
    staleTime: Infinity, // catalogue only changes with deploys
  });
}
