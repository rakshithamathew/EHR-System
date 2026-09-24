import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { getEhrs, syncEhr } from "../api/ehr";
import { patientQueryKeys } from "./usePatients";

export const ehrQueryKeys = {
  all: ["ehrs"] as const,
};

export function useEhrs() {
  return useQuery({
    queryKey: ehrQueryKeys.all,
    queryFn: getEhrs,
  });
}

export function useSyncEhr() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: syncEhr,
    onSuccess: async (_result, source) => {
      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: patientQueryKeys.bySource(source),
        }),
        queryClient.invalidateQueries({ queryKey: ehrQueryKeys.all }),
      ]);
    },
  });
}
