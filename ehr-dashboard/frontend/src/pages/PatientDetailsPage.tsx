import { Link, useParams } from "react-router-dom";

import { ErrorState } from "../components/common/ErrorState";
import { LoadingState } from "../components/common/LoadingState";
import { usePatient } from "../hooks/usePatient";

export function PatientDetailsPage() {
  const { patientId } = useParams<{ patientId: string }>();
  const patientQuery = usePatient(patientId);

  if (!patientId) {
    return <ErrorState error={new Error("A patient ID is required.")} />;
  }

  if (patientQuery.isPending) {
    return <LoadingState message="Loading patient..." />;
  }

  if (patientQuery.isError) {
    return <ErrorState error={patientQuery.error} />;
  }

  const { patient, conditions, medications } = patientQuery.data;

  return (
    <main className="mx-auto w-full max-w-5xl px-4 py-10 sm:px-6 lg:px-8">
      <Link className="text-sm font-medium text-blue-700 hover:underline" to="/">
        Back to patients
      </Link>
      <h1 className="mt-6 text-3xl font-semibold tracking-tight text-slate-950">
        {patient.name || patient.external_id}
      </h1>
      <div className="mt-4 space-y-1 text-sm text-slate-600">
        <p>{conditions.length} conditions</p>
        <p>{medications.length} medications</p>
      </div>
    </main>
  );
}
