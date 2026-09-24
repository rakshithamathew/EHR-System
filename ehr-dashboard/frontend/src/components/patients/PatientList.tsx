import type { PatientSummary } from "../../types/patient";
import { EmptyState } from "../common/EmptyState";
import { PatientListItem } from "./PatientListItem";

interface PatientListProps {
  patients: PatientSummary[];
}

export function PatientList({ patients }: PatientListProps) {
  if (patients.length === 0) {
    return <EmptyState message="No patients found." />;
  }

  return (
    <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
      <div className="grid grid-cols-[minmax(0,1fr)_8rem_6rem] gap-4 border-b border-slate-200 bg-slate-50 px-4 py-3 text-xs font-semibold uppercase tracking-wide text-slate-500 sm:grid-cols-[minmax(0,1fr)_10rem_8rem]">
        <span>Name</span>
        <span>DOB</span>
        <span>Gender</span>
      </div>
      <ul className="divide-y divide-slate-200">
        {patients.map((patient) => (
          <PatientListItem key={patient.id} patient={patient} />
        ))}
      </ul>
    </div>
  );
}
