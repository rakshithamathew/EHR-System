import { useQuery } from "@tanstack/react-query";

import { getPatients } from "../api/patients";

export const patientQueryKeys = {
  all: ["patients"] as const,
  bySource: (source: string) =>
    [...patientQueryKeys.all, "list", source] as const,
  list: (source: string, search: string | undefined, limit: number, page: number) =>
    [
      ...patientQueryKeys.bySource(source),
      search ?? "",
      limit,
      page,
    ] as const,
};

export function usePatients(
  source: string,
  search?: string,
  limit = 20,
  page = 1,
  enabled = true,
) {
  const normalizedSearch = search?.trim() || undefined;

  return useQuery({
    queryKey: patientQueryKeys.list(source, normalizedSearch, limit, page),
    queryFn: () => getPatients(source, normalizedSearch, limit, page),
    enabled: source.length > 0 && enabled,
    staleTime: 60_000,
    gcTime: 5 * 60_000,
    retry: false,
    retryOnMount: false,
    refetchOnMount: false,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
  });
}
