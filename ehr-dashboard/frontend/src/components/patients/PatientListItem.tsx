import { Link } from "react-router-dom";

import type { PatientSummary } from "../../types/patient";

interface PatientListItemProps {
  patient: PatientSummary;
}

export function PatientListItem({ patient }: PatientListItemProps) {
  return (
    <li>
      <Link
        to={`/patients/${patient.id}`}
        className="grid grid-cols-[minmax(0,1fr)_8rem_6rem] gap-4 px-4 py-4 text-sm text-slate-600 hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-blue-600 sm:grid-cols-[minmax(0,1fr)_10rem_8rem]"
      >
        <span className="truncate font-medium text-slate-900">
          {patient.name || patient.external_id}
        </span>
        <span>{patient.birth_date ?? "—"}</span>
        <span className="capitalize">{patient.gender ?? "—"}</span>
      </Link>
    </li>
  );
}
