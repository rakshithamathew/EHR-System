import { useQuery } from "@tanstack/react-query";

import { getPatient } from "../api/patients";
import { patientQueryKeys } from "./usePatients";

export function usePatient(patientId: string | undefined) {
  return useQuery({
    queryKey: [...patientQueryKeys.all, "detail", patientId ?? ""] as const,
    queryFn: () => {
      if (!patientId) {
        throw new Error("A patient ID is required.");
      }

      return getPatient(patientId);
    },
    enabled: Boolean(patientId),
  });
}
