import { useQuery } from "@tanstack/react-query";

import { getPatient } from "../api/patients";
import { patientQueryKeys } from "./usePatients";

export function usePatient(patientId: string | undefined, source?: string) {
  return useQuery({
    queryKey: [
      ...patientQueryKeys.all,
      "detail",
      source ?? "",
      patientId ?? "",
    ] as const,
    queryFn: () => {
      if (!patientId) {
        throw new Error("A patient ID is required.");
      }

      return getPatient(patientId, source);
    },
    enabled: Boolean(patientId),
  });
}
