import { useQuery } from "@tanstack/react-query";

import { getPatients } from "../api/patients";

export const patientQueryKeys = {
  all: ["patients"] as const,
  bySource: (source: string) =>
    [...patientQueryKeys.all, "list", source] as const,
  list: (source: string, search: string | undefined, limit: number, offset: number) =>
    [
      ...patientQueryKeys.bySource(source),
      search ?? "",
      limit,
      offset,
    ] as const,
};

export function usePatients(
  source: string,
  search?: string,
  limit = 20,
  offset = 0,
) {
  const normalizedSearch = search?.trim() || undefined;

  return useQuery({
    queryKey: patientQueryKeys.list(source, normalizedSearch, limit, offset),
    queryFn: () => getPatients(source, normalizedSearch, limit, offset),
    enabled: source.length > 0,
  });
}
