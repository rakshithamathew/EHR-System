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
