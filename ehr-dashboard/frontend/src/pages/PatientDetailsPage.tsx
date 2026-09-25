import { Link, useParams } from "react-router-dom";

import { EmptyState } from "../components/common/EmptyState";
import { ErrorState } from "../components/common/ErrorState";
import { LoadingState } from "../components/common/LoadingState";
import { usePatient } from "../hooks/usePatient";
import { formatDate, formatEhrSource } from "../utils/format";

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
        className={`mt-1.5 break-words text-base font-medium text-slate-900 ${capitalize ? "capitalize" : ""}`}
      >
        {value}
      </dd>
    </div>
  );
}

export function PatientDetailsPage() {
  const { patientId } = useParams<{ patientId: string }>();
  const patientQuery = usePatient(patientId);

  return (
    <main className="mx-auto w-full max-w-6xl px-4 py-8 sm:px-6 sm:py-10 lg:px-8">
      <Link
        className="inline-flex items-center gap-2 text-sm font-semibold text-teal-700 hover:text-teal-900 focus:outline-none focus:ring-2 focus:ring-teal-600 focus:ring-offset-2"
        to="/"
      >
        <svg
          aria-hidden="true"
          viewBox="0 0 20 20"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.75"
          className="h-4 w-4"
        >
          <path d="m12.5 15-5-5 5-5" />
        </svg>
        Back to Patients
      </Link>

      {!patientId ? (
        <div className="mt-6">
          <ErrorState error={new Error("A patient ID is required.")} />
        </div>
      ) : patientQuery.isPending ? (
        <div className="mt-6">
          <LoadingState message="Loading patient..." />
        </div>
      ) : patientQuery.isError ? (
        <div className="mt-6">
          <ErrorState error={patientQuery.error} />
        </div>
      ) : (
        <>
          <header className="mt-7 border-b border-slate-200 pb-6">
            <h1 className="text-2xl font-semibold tracking-tight text-slate-950 sm:text-3xl">
              {patientQuery.data.patient.name ||
                patientQuery.data.patient.external_id}
            </h1>
          </header>

          <section className="mt-8" aria-labelledby="patient-information-heading">
            <h2
              id="patient-information-heading"
              className="text-xl font-semibold text-slate-950"
            >
              Patient Information
            </h2>
            <dl className="mt-4 grid gap-6 rounded-xl border border-slate-200 border-l-4 border-l-teal-600 bg-white p-5 shadow-sm sm:grid-cols-2 sm:p-6 lg:grid-cols-4">
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

          <section className="mt-10" aria-labelledby="conditions-heading">
            <div className="mb-4 flex items-center gap-3">
              <h2
                id="conditions-heading"
                className="text-xl font-semibold text-slate-950"
              >
                Conditions
              </h2>
              <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-600">
                {patientQuery.data.conditions.length}
              </span>
            </div>
            {patientQuery.data.conditions.length === 0 ? (
              <EmptyState message="No conditions found for this patient." />
            ) : (
              <ul className="divide-y divide-slate-200 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
                {patientQuery.data.conditions.map((condition) => (
                  <li key={condition.id} className="p-5 sm:p-6">
                    <h3 className="text-lg font-semibold text-slate-950">
                      {condition.display || "Unnamed condition"}
                    </h3>
                    <dl className="mt-5 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
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

          <section className="mt-10" aria-labelledby="medications-heading">
            <div className="mb-4 flex items-center gap-3">
              <h2
                id="medications-heading"
                className="text-xl font-semibold text-slate-950"
              >
                Medications
              </h2>
              <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-600">
                {patientQuery.data.medications.length}
              </span>
            </div>
            {patientQuery.data.medications.length === 0 ? (
              <EmptyState message="No medications found for this patient." />
            ) : (
              <ul className="divide-y divide-slate-200 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
                {patientQuery.data.medications.map((medication) => (
                  <li key={medication.id} className="p-5 sm:p-6">
                    <h3 className="text-lg font-semibold text-slate-950">
                      {medication.medication_display || "Unnamed medication"}
                    </h3>
                    <dl className="mt-5 grid gap-5 sm:grid-cols-3">
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
