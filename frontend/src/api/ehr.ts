import axios from "axios";

import { apiClient } from "./client";
import type { EhrSource, SyncResult } from "../types/ehr";

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

interface ApiErrorResponse {
  error?: string;
  detail?: string;
}

function redirectEpicLogin(error: unknown, source: string): boolean {
  if (
    source === "epic" &&
    axios.isAxiosError<ApiErrorResponse>(error) &&
    error.response?.status === 401 &&
    error.response.data?.error === "epic_auth_required"
  ) {
    window.location.assign(getEpicLoginUrl());
    return true;
  }
  return false;
}

export async function getEhrs(): Promise<EhrSource[]> {
  const response = await apiClient.get<SourceResponse[]>("/api/sources");
  return response.data.map((source) => ({
    code: source.id,
    name: source.label,
    enabled: source.enabled,
    last_sync: source.last_sync,
  }));
}

export async function syncEhr(source: string): Promise<SyncResult> {
  try {
    const response = await apiClient.post<DatabaseSyncResponse>("/api/sync", null, {
      params: { source },
    });
    return {
      source,
      status: "completed",
      patients_processed: response.data.patients,
      conditions_processed: response.data.conditions,
      medications_processed: response.data.medications,
    };
  } catch (error) {
    if (redirectEpicLogin(error, source)) {
      return new Promise<SyncResult>(() => undefined);
    }
    if (axios.isAxiosError<ApiErrorResponse>(error) && error.response?.data?.detail) {
      throw new Error(error.response.data.detail);
    }
    throw error;
  }
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

export async function disconnectEpic(): Promise<EpicConnectionStatus> {
  const response = await apiClient.post<EpicConnectionStatus>("/api/epic/logout");
  return response.data;
}
