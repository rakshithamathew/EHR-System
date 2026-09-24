import { apiClient } from "./client";
import type { PatientDetails, PatientSummary } from "../types/patient";

export async function getPatients(
  source: string,
  search?: string,
): Promise<PatientSummary[]> {
  const response = await apiClient.get<PatientSummary[]>("/api/patients", {
    params: {
      source,
      search: search?.trim() || undefined,
    },
  });
  return response.data;
}

export async function getPatient(patientId: string): Promise<PatientDetails> {
  const response = await apiClient.get<PatientDetails>(
    `/api/patients/${encodeURIComponent(patientId)}`,
  );
  return response.data;
}
