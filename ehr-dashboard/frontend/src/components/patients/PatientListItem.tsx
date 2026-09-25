import { Link, useNavigate } from "react-router-dom";

import type { PatientSummary } from "../../types/patient";
import { formatDate, formatEhrSource } from "../../utils/format";

interface PatientListItemProps {
  patient: PatientSummary;
}

export function PatientListItem({ patient }: PatientListItemProps) {
  const navigate = useNavigate();
  const patientName = patient.name || patient.external_id;

  function openPatient() {
    navigate(`/patients/${patient.id}`);
  }

  return (
    <tr
      onClick={openPatient}
      className="group cursor-pointer text-base text-slate-600 hover:bg-teal-50/40"
    >
      <td className="px-5 py-4 font-semibold text-slate-900 group-hover:text-teal-800">
        <Link
          to={`/patients/${patient.id}`}
          onClick={(event) => event.stopPropagation()}
          className="rounded-sm outline-none focus-visible:ring-2 focus-visible:ring-teal-600 focus-visible:ring-offset-2"
        >
          {patientName}
        </Link>
      </td>
      <td className="whitespace-nowrap px-5 py-4">
        {formatDate(patient.birth_date)}
      </td>
      <td className="px-5 py-4 capitalize">
        {patient.gender || "Not recorded"}
      </td>
      <td className="px-5 py-4">
        <span className="inline-flex rounded-full bg-teal-50 px-2.5 py-1 text-sm font-medium text-teal-800 ring-1 ring-inset ring-teal-200">
          {formatEhrSource(patient.source)}
        </span>
      </td>
    </tr>
  );
}
