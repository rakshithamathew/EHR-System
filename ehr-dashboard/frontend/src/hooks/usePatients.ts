import { useQuery } from "@tanstack/react-query";

import { getPatients } from "../api/patients";

export const patientQueryKeys = {
  all: ["patients"] as const,
  bySource: (source: string) =>
    [...patientQueryKeys.all, "list", source] as const,
  list: (source: string, search?: string) =>
    [...patientQueryKeys.bySource(source), search ?? ""] as const,
};

export function usePatients(source: string, search?: string) {
  return useQuery({
    queryKey: patientQueryKeys.list(source, search),
    queryFn: () => getPatients(source, search),
    enabled: source.length > 0,
  });
}
