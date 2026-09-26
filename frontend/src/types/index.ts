export interface LastSync {
  status: string;
  started_at: string;
  completed_at: string | null;
  patients_processed: number;
  conditions_processed: number;
  medications_processed: number;
  error_message: string | null;
}

export interface EhrSource {
  code: string;
  name: string;
  enabled: boolean;
  last_sync: LastSync | null;
}

export interface SyncResult {
  source: string;
  status: string;
  patients_processed: number;
  conditions_processed: number;
  medications_processed: number;
}

export interface PatientSummary {
  id: string;
  source: string;
  external_id: string;
  name: string | null;
  given_name: string | null;
  family_name: string | null;
  gender: string | null;
  birth_date: string | null;
  condition_count: number;
  medication_count: number;
  last_synced_at: string | null;
}

export interface PatientPage {
  items: PatientSummary[];
  page: number;
  page_size: number;
  total: number;
  has_next: boolean;
}

export interface Condition {
  id: string;
  external_id: string;
  clinical_status: string | null;
  verification_status: string | null;
  code: string | null;
  code_system: string | null;
  display: string | null;
  onset_date: string | null;
}

export interface Medication {
  id: string;
  external_id: string;
  status: string | null;
  medication_code: string | null;
  medication_display: string | null;
  authored_on: string | null;
}

export interface PatientDetails {
  patient: PatientSummary;
  conditions: Condition[];
  medications: Medication[];
}
