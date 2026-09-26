import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ApiError, apiBaseUrl, apiRequest } from "./client";
import type { EhrSource, SyncResult } from "../types";

export interface EpicConnectionStatus {
  connected: boolean;
}

interface SourceResponse {
  id: string;
  label: string;
  enabled: boolean;
  last_sync: EhrSource["last_sync"];
}

interface DatabaseSyncResponse {
  synced: number;
  patients: number;
  conditions: number;
  medications: number;
}

function redirectEpicLogin(error: unknown, source: string): boolean {
  if (
    source === "epic" &&
    error instanceof ApiError &&
    error.status === 401 &&
    error.data.error === "epic_auth_required"
  ) {
    window.location.assign(getEpicLoginUrl());
    return true;
  }
  return false;
}

export async function getEhrs(): Promise<EhrSource[]> {
  const response = await apiRequest<SourceResponse[]>("/api/sources");
  return response.map((source) => ({
    code: source.id,
    name: source.label,
    enabled: source.enabled,
    last_sync: source.last_sync,
  }));
}

export async function syncEhr(source: string): Promise<SyncResult> {
  try {
    const response = await apiRequest<DatabaseSyncResponse>(`/api/sync?source=${encodeURIComponent(source)}`, { method: "POST" });
    return {
      source,
      status: "completed",
      patients_processed: response.patients,
      conditions_processed: response.conditions,
      medications_processed: response.medications,
    };
  } catch (error) {
    if (redirectEpicLogin(error, source)) {
      return new Promise<SyncResult>(() => undefined);
    }
    if (error instanceof ApiError) {
      throw new Error(error.message);
    }
    throw error;
  }
}

export function getEpicLoginUrl(): string {
  return new URL("/api/epic/login", apiBaseUrl).toString();
}

export function getEpicCallbackUrl(search: string): string {
  const callbackUrl = new URL("/api/epic/callback", apiBaseUrl);
  callbackUrl.search = search;
  return callbackUrl.toString();
}

export async function getEpicConnectionStatus(): Promise<EpicConnectionStatus> {
  return apiRequest<EpicConnectionStatus>("/api/epic/status");
}

export async function disconnectEpic(): Promise<EpicConnectionStatus> {
  return apiRequest<EpicConnectionStatus>("/api/epic/logout", { method: "POST" });
}

export const ehrQueryKeys = { all: ["ehrs"] as const };
export const patientQueryKeys = {
  all: ["patients"] as const,
  bySource: (source: string) => ["patients", "list", source] as const,
};

export function useEhrs() {
  return useQuery({ queryKey: ehrQueryKeys.all, queryFn: getEhrs, staleTime: Infinity, gcTime: Infinity, retry: false, refetchOnWindowFocus: false });
}

export function useSyncEhr() {
  const queryClient = useQueryClient();
  return useMutation({ mutationFn: syncEhr, onSuccess: async (_, source) => {
    await queryClient.invalidateQueries({ queryKey: patientQueryKeys.bySource(source) });
    await queryClient.invalidateQueries({ queryKey: ehrQueryKeys.all });
  }});
}

export function useEpicConnectionStatus(enabled: boolean) {
  return useQuery({ queryKey: [...ehrQueryKeys.all, "epic-status"], queryFn: getEpicConnectionStatus, enabled, staleTime: 30_000, retry: false });
}

export function useDisconnectEpic() {
  const queryClient = useQueryClient();
  return useMutation({ mutationFn: disconnectEpic, onSuccess: (value) => queryClient.setQueryData([...ehrQueryKeys.all, "epic-status"], value) });
}
