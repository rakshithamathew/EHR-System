import { useQuery } from "@tanstack/react-query";

import { ApiError, apiRequest } from "./client";
import { getEpicLoginUrl } from "./ehr";
import { patientQueryKeys } from "./ehr";
import type { PatientDetails, PatientPage } from "../types";

export function usePatients(source: string, search?: string, limit = 10, page = 1, sortBy = "name", sortOrder: "asc" | "desc" = "asc", enabled = true) {
  const term = search?.trim() || undefined;
  return useQuery({
    queryKey: [...patientQueryKeys.bySource(source), term ?? "", limit, page, sortBy, sortOrder],
    queryFn: () => getPatients(source, term, limit, page, sortBy, sortOrder),
    enabled: Boolean(source) && enabled, staleTime: 60_000, gcTime: 300_000, retry: false, refetchOnWindowFocus: false,
  });
}

export function usePatient(patientId: string | undefined, source?: string) {
  return useQuery({
    queryKey: [...patientQueryKeys.all, "detail", source ?? "", patientId ?? ""],
    queryFn: () => patientId ? getPatient(patientId, source) : Promise.reject(new Error("A patient ID is required.")),
    enabled: Boolean(patientId),
  });
}

function readableApiError(error: unknown, source?: string): never {
  if (error instanceof ApiError) {
    if (
      source === "epic" &&
      error.status === 401 &&
      error.data.error === "epic_auth_required"
    ) {
      window.location.assign(getEpicLoginUrl());
      throw new Error("Redirecting to Epic authorization");
    }
    const detail = error.data.detail;
    if (detail) {
      throw new Error(detail);
    }
  }
  throw error;
}

export async function getPatients(
  source: string,
  search?: string,
  limit = 20,
  page = 1,
  sortBy = "name",
  sortOrder: "asc" | "desc" = "asc",
): Promise<PatientPage> {
  try {
    const params = new URLSearchParams({ source, limit: String(limit), page: String(page), sort_by: sortBy, sort_order: sortOrder });
    if (search?.trim()) params.set("search", search.trim());
    return await apiRequest<PatientPage>(`/api/patients?${params}`);
  } catch (error) {
    return readableApiError(error, source);
  }
}

export async function getPatient(
  patientId: string,
  source?: string,
): Promise<PatientDetails> {
  try {
    const suffix = source ? `?source=${encodeURIComponent(source)}` : "";
    return await apiRequest<PatientDetails>(`/api/patients/${encodeURIComponent(patientId)}${suffix}`);
  } catch (error) {
    return readableApiError(error, source);
  }
}
