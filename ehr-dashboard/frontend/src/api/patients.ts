import axios from "axios";

import { apiClient } from "./client";
import { getEpicLoginUrl } from "./ehr";
import type {
  PatientDetails,
  PatientPage,
  PatientSummary,
} from "../types/patient";

interface FhirPatientSummary {
  id: string;
  name: string | null;
  gender: string | null;
  birthDate: string | null;
}

interface FhirPatientPage {
  items: FhirPatientSummary[];
  page: number;
  has_next: boolean;
}

interface ApiErrorResponse {
  detail?: string;
  error?: string;
}

function redirectForEpicAuthorization(error: unknown, source?: string): boolean {
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

export async function getPatients(
  source: string,
  search?: string,
  limit = 20,
  page = 1,
): Promise<PatientPage> {
  try {
    const response = await apiClient.get<FhirPatientPage>("/api/patients", {
      params: {
        source,
        search: search?.trim() || undefined,
        limit,
        page,
      },
      timeout: 15_000,
    });
    return {
      items: response.data.items.map((patient): PatientSummary => ({
        id: patient.id,
        source,
        external_id: patient.id,
        name: patient.name,
        given_name: null,
        family_name: null,
        gender: patient.gender,
        birth_date: patient.birthDate,
      })),
      page: response.data.page,
      has_next: response.data.has_next,
    };
  } catch (error) {
    if (redirectForEpicAuthorization(error, source)) {
      return await new Promise<PatientPage>(() => undefined);
    }
    if (axios.isAxiosError<ApiErrorResponse>(error)) {
      const detail = error.response?.data?.detail;
      if (detail) {
        throw new Error(detail);
      }
    }
    throw error;
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
    if (redirectForEpicAuthorization(error, source)) {
      return await new Promise<PatientDetails>(() => undefined);
    }
    if (axios.isAxiosError<ApiErrorResponse>(error)) {
      const detail = error.response?.data?.detail;
      if (detail) {
        throw new Error(detail);
      }
    }
    throw error;
  }
}
