import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { getEhrs, getEpicConnectionStatus, syncEhr } from "../api/ehr";
import { patientQueryKeys } from "./usePatients";

export const ehrQueryKeys = {
  all: ["ehrs"] as const,
};

export function useEhrs() {
  return useQuery({
    queryKey: ehrQueryKeys.all,
    queryFn: getEhrs,
    staleTime: Infinity,
    gcTime: Infinity,
    retry: false,
    refetchOnMount: false,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
  });
}

export function useSyncEhr() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: syncEhr,
    onSuccess: async (result, source) => {
      if (result.status !== "completed") {
        return;
      }
      await queryClient.invalidateQueries({
        queryKey: patientQueryKeys.bySource(source),
      });
    },
  });
}

export function useEpicConnectionStatus(enabled: boolean) {
  return useQuery({
    queryKey: [...ehrQueryKeys.all, "epic-status"] as const,
    queryFn: getEpicConnectionStatus,
    enabled,
    staleTime: 30_000,
    retry: false,
    refetchOnWindowFocus: false,
  });
}
