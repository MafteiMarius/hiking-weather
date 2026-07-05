import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import type { SavedLocation, SavedLocationCreate } from "@/types/api";

export function useSavedLocations(enabled: boolean) {
  return useQuery<SavedLocation[]>({
    queryKey: ["saved-locations"],
    queryFn: async () => {
      const { data } = await api.get<SavedLocation[]>("/locations");
      return data;
    },
    enabled, // only when logged in — the endpoint 401s otherwise
    staleTime: 1000 * 60 * 5,
  });
}

export function useSaveLocation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: SavedLocationCreate) => {
      const { data } = await api.post<SavedLocation>("/locations", body);
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["saved-locations"] }),
  });
}

export function useDeleteLocation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/locations/${id}`);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["saved-locations"] }),
  });
}
