import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import type { Profile, ProfileUpdate } from "@/types/api";

export function useProfile(enabled: boolean) {
  return useQuery<Profile>({
    queryKey: ["profile"],
    queryFn: async () => {
      const { data } = await api.get<Profile>("/profile");
      return data;
    },
    enabled, // only while the dialog is open — the endpoint 401s otherwise
    staleTime: 1000 * 60 * 5,
  });
}

export function useUpdateProfile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: ProfileUpdate) => {
      const { data } = await api.patch<Profile>("/profile", body);
      return data;
    },
    onSuccess: (data) => {
      // PATCH returns the full updated profile — write it into the cache
      // directly instead of refetching what we already hold.
      qc.setQueryData(["profile"], data);
      // Rankings are computed FROM the profile (filters + penalties), so any
      // cached recommendation list is stale the moment the profile changes.
      qc.invalidateQueries({ queryKey: ["recommendations"] });
    },
  });
}
