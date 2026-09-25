import axios from "axios";

import { apiClient } from "./client";
import { getEpicLoginUrl } from "./ehr";
import type { PatientDetails, PatientPage } from "../types/patient";

interface ApiErrorResponse {
  error?: string;
  detail?: string;
}

function readableApiError(error: unknown, source?: string): never {
  if (axios.isAxiosError<ApiErrorResponse>(error)) {
    if (
      source === "epic" &&
      error.response?.status === 401 &&
      error.response.data?.error === "epic_auth_required"
    ) {
      window.location.assign(getEpicLoginUrl());
      throw new Error("Redirecting to Epic authorization");
    }
    const detail = error.response?.data?.detail;
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
    const response = await apiClient.get<PatientPage>("/api/patients", {
      params: {
        source,
        search: search?.trim() || undefined,
        limit,
        page,
        sort_by: sortBy,
        sort_order: sortOrder,
      },
    });
    return response.data;
  } catch (error) {
    return readableApiError(error, source);
  }
}

export async function getPatient(
  patientId: string,
  source?: string,
): Promise<PatientDetails> {
  try {
    const response = await apiClient.get<PatientDetails>(
      `/api/patients/${encodeURIComponent(patientId)}`,
      { params: { source: source || undefined } },
    );
    return response.data;
  } catch (error) {
    return readableApiError(error, source);
  }
}
