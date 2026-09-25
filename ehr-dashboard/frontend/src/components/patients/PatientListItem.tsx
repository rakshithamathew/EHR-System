import { Link, useNavigate } from "react-router-dom";

import type { PatientSummary } from "../../types/patient";
import {
  ehrSourceBadgeClasses,
  formatDate,
  formatEhrSource,
  getPatientSourceUrl,
} from "../../utils/format";

interface PatientListItemProps {
  patient: PatientSummary;
}

export function PatientListItem({ patient }: PatientListItemProps) {
  const navigate = useNavigate();
  const patientName = patient.name || patient.external_id;
  const patientUrl = `/patients/${encodeURIComponent(patient.id)}?source=${encodeURIComponent(patient.source)}`;
  const sourceUrl = getPatientSourceUrl(patient.source, patient.external_id);

  function openPatient() {
    navigate(patientUrl);
  }

  return (
    <tr
      onClick={openPatient}
      className="group cursor-pointer text-base text-slate-600 hover:bg-teal-50/40"
    >
      <td className="px-5 py-4 font-semibold text-slate-900 group-hover:text-teal-800">
        <Link
          to={patientUrl}
          onClick={(event) => event.stopPropagation()}
          className="rounded-sm outline-none focus-visible:ring-2 focus-visible:ring-teal-600 focus-visible:ring-offset-2"
        >
          {patientName}
        </Link>
      </td>
      <td className="max-w-64 truncate px-5 py-4 font-mono text-sm text-slate-600">
        {patient.external_id}
      </td>
      <td className="whitespace-nowrap px-5 py-4">
        {formatDate(patient.birth_date)}
      </td>
      <td className="px-5 py-4 capitalize">
        {patient.gender || "Not recorded"}
      </td>
      <td className="px-5 py-4">
        <div className="flex flex-wrap gap-2">
          <span className="inline-flex rounded-full bg-blue-50 px-2.5 py-1 text-xs font-semibold text-blue-800 ring-1 ring-inset ring-blue-200">
            {patient.condition_count} conditions
          </span>
          <span className="inline-flex rounded-full bg-cyan-50 px-2.5 py-1 text-xs font-semibold text-cyan-800 ring-1 ring-inset ring-cyan-200">
            {patient.medication_count} medications
          </span>
        </div>
      </td>
      <td className="px-5 py-4">
        <span
          className={`inline-flex rounded-full px-2.5 py-1 text-sm font-medium ring-1 ring-inset ${ehrSourceBadgeClasses(patient.source)}`}
        >
          {formatEhrSource(patient.source)}
        </span>
      </td>
      <td className="whitespace-nowrap px-5 py-4">
        {sourceUrl && (
          <a
            href={sourceUrl}
            target="_blank"
            rel="noreferrer"
            onClick={(event) => event.stopPropagation()}
            className="font-semibold text-teal-700 hover:text-teal-900 hover:underline focus:outline-none focus:ring-2 focus:ring-teal-600 focus:ring-offset-2"
          >
            Open in source EHR
          </a>
        )}
      </td>
    </tr>
  );
}
