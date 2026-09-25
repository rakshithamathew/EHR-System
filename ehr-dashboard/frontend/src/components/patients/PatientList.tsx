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
    <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
      <table className="min-w-[720px] w-full border-collapse text-left">
        <thead className="bg-slate-50">
          <tr className="border-b border-slate-200">
            <th className="px-5 py-3.5 text-xs font-semibold uppercase tracking-wider text-slate-500">
              Name
            </th>
            <th className="px-5 py-3.5 text-xs font-semibold uppercase tracking-wider text-slate-500">
              Patient ID
            </th>
            <th className="px-5 py-3.5 text-xs font-semibold uppercase tracking-wider text-slate-500">
              DOB
            </th>
            <th className="px-5 py-3.5 text-xs font-semibold uppercase tracking-wider text-slate-500">
              Gender
            </th>
            <th className="px-5 py-3.5 text-xs font-semibold uppercase tracking-wider text-slate-500">
              EHR Source
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {patients.map((patient) => (
            <PatientListItem key={patient.id} patient={patient} />
          ))}
        </tbody>
      </table>
    </div>
  );
}
