import { Link, useParams, useSearchParams } from "react-router-dom";

import { EmptyState, ErrorState, LoadingState } from "../components/Status";
import { usePatient } from "../api/patients";
import {
  formatDate,
  formatEhrSource,
  getPatientSourceUrl,
} from "../api/format";

function displayValue(value: string | null): string {
  return value || "Not recorded";
}

interface DetailFieldProps {
  label: string;
  value: string;
  capitalize?: boolean;
}

function DetailField({ label, value, capitalize = false }: DetailFieldProps) {
  return (
    <div>
      <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">
        {label}
      </dt>
      <dd
        className={`mt-1 break-words text-sm font-medium text-slate-900 ${capitalize ? "capitalize" : ""}`}
      >
        {value}
      </dd>
    </div>
  );
}

export function PatientDetailsPage() {
  const { patientId } = useParams<{ patientId: string }>();
  const [searchParams] = useSearchParams();
  const patientQuery = usePatient(patientId, searchParams.get("source") ?? undefined);
  const selectedSource =
    searchParams.get("source") ?? patientQuery.data?.patient.source ?? null;
  const patientDirectoryUrl = selectedSource
    ? `/dashboard?source=${encodeURIComponent(selectedSource)}`
    : "/dashboard";
  const sourceUrl = patientQuery.data
    ? getPatientSourceUrl(
        patientQuery.data.patient.source,
        patientQuery.data.patient.external_id,
      )
    : null;

  return (
    <main className="w-full p-[3px]">
      <Link
        className="inline-flex items-center gap-1.5 text-xs font-semibold text-teal-700 hover:text-teal-900 focus:outline-none focus:ring-2 focus:ring-teal-600 focus:ring-offset-2"
        to={patientDirectoryUrl}
      >
        <svg
          aria-hidden="true"
          viewBox="0 0 20 20"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.75"
          className="h-3.5 w-3.5"
        >
          <path d="m12.5 15-5-5 5-5" />
        </svg>
        Back to Patients
      </Link>

      {!patientId ? (
        <div className="mt-3">
          <ErrorState error={new Error("A patient ID is required.")} />
        </div>
      ) : patientQuery.isPending ? (
        <div className="mt-3">
          <LoadingState message="Loading patient..." />
        </div>
      ) : patientQuery.isError ? (
        <div className="mt-3">
          <ErrorState error={patientQuery.error} />
        </div>
      ) : (
        <>
          <header className="mt-4 flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 pb-3">
            <h1 className="text-xl font-semibold tracking-tight text-slate-950">
              {patientQuery.data.patient.name ||
                patientQuery.data.patient.external_id}
            </h1>
            {sourceUrl && (
              <a
                href={sourceUrl}
                target="_blank"
                rel="noreferrer"
                className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-teal-700 hover:bg-slate-50 hover:text-teal-900 focus:outline-none focus:ring-2 focus:ring-teal-600 focus:ring-offset-2"
              >
                Open in source EHR
              </a>
            )}
          </header>

          <section className="mt-4" aria-labelledby="patient-information-heading">
            <h2
              id="patient-information-heading"
              className="text-base font-semibold text-slate-950"
            >
              Patient Information
            </h2>
            <dl className="mt-2 grid gap-3 rounded-lg border border-slate-200 border-l-4 border-l-teal-600 bg-white p-3 shadow-sm sm:grid-cols-2 lg:grid-cols-4">
              <DetailField
                label="Name"
                value={
                  patientQuery.data.patient.name ||
                  patientQuery.data.patient.external_id
                }
              />
              <DetailField
                label="DOB"
                value={formatDate(patientQuery.data.patient.birth_date)}
              />
              <DetailField
                label="Gender"
                value={displayValue(patientQuery.data.patient.gender)}
                capitalize
              />
              <DetailField
                label="Source"
                value={formatEhrSource(patientQuery.data.patient.source)}
              />
            </dl>
          </section>

          <section className="mt-5" aria-labelledby="conditions-heading">
            <div className="mb-2 flex items-center gap-2">
              <h2
                id="conditions-heading"
                className="text-base font-semibold text-slate-950"
              >
                Conditions
              </h2>
              <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-semibold text-slate-600">
                {patientQuery.data.conditions.length}
              </span>
            </div>
            {patientQuery.data.conditions.length === 0 ? (
              <EmptyState message="No conditions found for this patient." />
            ) : (
              <ul className="divide-y divide-slate-200 overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
                {patientQuery.data.conditions.map((condition) => (
                  <li key={condition.id} className="p-3">
                    <h3 className="text-sm font-semibold text-slate-950">
                      {condition.display || "Unnamed condition"}
                    </h3>
                    <dl className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                      <DetailField
                        label="Clinical status"
                        value={displayValue(condition.clinical_status)}
                        capitalize
                      />
                      <DetailField
                        label="Code"
                        value={displayValue(condition.code)}
                      />
                      <DetailField
                        label="Code system"
                        value={displayValue(condition.code_system)}
                      />
                      <DetailField
                        label="Onset date"
                        value={formatDate(condition.onset_date)}
                      />
                    </dl>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="mt-5" aria-labelledby="medications-heading">
            <div className="mb-2 flex items-center gap-2">
              <h2
                id="medications-heading"
                className="text-base font-semibold text-slate-950"
              >
                Medications
              </h2>
              <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-semibold text-slate-600">
                {patientQuery.data.medications.length}
              </span>
            </div>
            {patientQuery.data.medications.length === 0 ? (
              <EmptyState message="No medications found for this patient." />
            ) : (
              <ul className="divide-y divide-slate-200 overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
                {patientQuery.data.medications.map((medication) => (
                  <li key={medication.id} className="p-3">
                    <h3 className="text-sm font-semibold text-slate-950">
                      {medication.medication_display || "Unnamed medication"}
                    </h3>
                    <dl className="mt-3 grid gap-3 sm:grid-cols-3">
                      <DetailField
                        label="Status"
                        value={displayValue(medication.status)}
                        capitalize
                      />
                      <DetailField
                        label="Code"
                        value={displayValue(medication.medication_code)}
                      />
                      <DetailField
                        label="Authored date"
                        value={formatDate(medication.authored_on)}
                      />
                    </dl>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </>
      )}
    </main>
  );
}
