import { useMutation } from "@tanstack/react-query";
import api from "@/lib/api";
import type { EquipmentPlan } from "@/types/api";

export interface EquipmentParams {
  lat: number;
  lng: number;
  date: string;
}

/**
 * Mutation, not query: each call costs real money on the backend's Anthropic
 * account, so it only fires on an explicit button press — never automatically.
 */
export function useEquipment() {
  return useMutation<EquipmentPlan, unknown, EquipmentParams>({
    mutationFn: async (params) => {
      const { data } = await api.post<EquipmentPlan>("/ai/equipment", params);
      return data;
    },
  });
}
