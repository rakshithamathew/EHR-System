import { apiClient } from "./client";
import type { EhrSource, SyncResult } from "../types/ehr";

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
