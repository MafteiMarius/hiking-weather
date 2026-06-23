import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import type { UserRead } from "@/types/api";

export function useMe() {
  return useQuery<UserRead | null>({
    queryKey: ["me"],
    queryFn: async () => {
      try {
        const { data } = await api.get<UserRead>("/users/me");
        return data;
      } catch {
        return null; // 401 = not logged in, not an error
      }
    },
    retry: false,
    staleTime: 1000 * 60 * 5,
  });
}

export function useLogin() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (creds: { email: string; password: string }) => {
      // fastapi-users login expects form data, not JSON
      const form = new URLSearchParams({
        username: creds.email,
        password: creds.password,
      });
      await api.post("/auth/jwt/login", form, {
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
      });
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["me"] }),
  });
}

export function useRegister() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (creds: { email: string; password: string }) => {
      await api.post("/auth/register", creds);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["me"] }),
  });
}

export function useLogout() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      await api.post("/auth/jwt/logout");
    },
    onSuccess: () => {
      qc.setQueryData(["me"], null);
      qc.invalidateQueries({ queryKey: ["me"] });
    },
  });
}
