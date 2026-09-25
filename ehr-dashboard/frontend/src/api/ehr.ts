import { apiClient } from "./client";
import type { EhrSource, SyncResult } from "../types/ehr";

export interface EpicConnectionStatus {
  connected: boolean;
}

export async function getEhrs(): Promise<EhrSource[]> {
  const response = await apiClient.get<EhrSource[]>("/api/ehrs");
  return response.data;
}

export async function syncEhr(source: string): Promise<SyncResult> {
  const response = await apiClient.post<SyncResult>(
    `/api/ehrs/${encodeURIComponent(source)}/sync`,
  );
  return response.data;
}

export function getEpicLoginUrl(): string {
  const baseUrl = apiClient.defaults.baseURL || window.location.origin;
  return new URL("/api/epic/login", baseUrl).toString();
}

export function getEpicCallbackUrl(search: string): string {
  const baseUrl = apiClient.defaults.baseURL || window.location.origin;
  const callbackUrl = new URL("/api/epic/callback", baseUrl);
  callbackUrl.search = search;
  return callbackUrl.toString();
}

export async function getEpicConnectionStatus(): Promise<EpicConnectionStatus> {
  const response = await apiClient.get<EpicConnectionStatus>("/api/epic/status");
  return response.data;
}
