import { Link, useNavigate } from "react-router-dom";
import type { PatientSummary } from "../types";
import { ehrSourceBadgeClasses, formatDate, formatEhrSource, getPatientSourceUrl } from "../api/format";

export interface PatientSort { id: string; desc: boolean }

interface Props {
  patients: PatientSummary[];
  sort: PatientSort;
  onSort: (sort: PatientSort) => void;
  page: number;
  pageSize: number;
  totalCount: number;
  onPageChange: (page: number) => void;
  onPageSizeChange: (size: number) => void;
}

const headers = [
  ["name", "Name"], ["external_id", "Patient ID"], ["birth_date", "DOB"],
  ["gender", "Gender"], ["", "Clinical data"], ["", "EHR Source"], ["", "Source record"],
] as const;

export function PatientList({ patients, sort, onSort, page, pageSize, totalCount, onPageChange, onPageSizeChange }: Props) {
  const navigate = useNavigate();
  const pages = Math.max(Math.ceil(totalCount / pageSize), 1);
  const changeSort = (id: string) => onSort({ id, desc: sort.id === id ? !sort.desc : false });

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="min-h-0 flex-1 overflow-auto rounded-md border border-slate-200 bg-white shadow-sm">
        <table className="w-full min-w-[960px] border-collapse text-left">
          <thead className="sticky top-0 z-10 bg-slate-50 shadow-[0_1px_0_0_rgb(226_232_240)]">
            <tr className="border-b border-slate-200">
              {headers.map(([id, label], index) => (
                <th key={`${label}-${index}`} className="px-2 py-1.5 text-[11px] font-semibold uppercase tracking-wide text-slate-500" aria-sort={id && sort.id === id ? (sort.desc ? "descending" : "ascending") : undefined}>
                  {id ? <button type="button" onClick={() => changeSort(id)} className="inline-flex items-center gap-1 rounded-sm hover:text-slate-900 focus:outline-none focus:ring-2 focus:ring-teal-600">{label}<span aria-hidden="true">{sort.id === id ? (sort.desc ? "↓" : "↑") : "↕"}</span></button> : label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {patients.length === 0 ? <tr><td colSpan={7} className="px-2 py-4 text-center text-sm text-slate-500">No patients found.</td></tr> : patients.map((patient) => {
              const detailUrl = `/patients/${encodeURIComponent(patient.id)}?source=${encodeURIComponent(patient.source)}`;
              const sourceUrl = getPatientSourceUrl(patient.source, patient.external_id);
              return (
                <tr key={patient.id} onClick={() => navigate(detailUrl)} className="group cursor-pointer text-sm text-slate-600 hover:bg-teal-50/40">
                  <td className="px-2 py-2"><Link to={detailUrl} onClick={(event) => event.stopPropagation()} className="font-semibold text-slate-900 hover:text-teal-800">{patient.name || patient.external_id}</Link></td>
                  <td className="px-2 py-2"><span className="block max-w-64 truncate font-mono text-xs">{patient.external_id}</span></td>
                  <td className="px-2 py-2 whitespace-nowrap">{formatDate(patient.birth_date)}</td>
                  <td className="px-2 py-2 capitalize">{patient.gender || "Not recorded"}</td>
                  <td className="px-2 py-2"><div className="flex flex-wrap gap-1"><span className="rounded-full bg-blue-50 px-2 py-0.5 text-[11px] font-semibold text-blue-800 ring-1 ring-blue-200">{patient.condition_count} conditions</span><span className="rounded-full bg-cyan-50 px-2 py-0.5 text-[11px] font-semibold text-cyan-800 ring-1 ring-cyan-200">{patient.medication_count} medications</span></div></td>
                  <td className="px-2 py-2"><span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ring-1 ${ehrSourceBadgeClasses(patient.source)}`}>{formatEhrSource(patient.source)}</span></td>
                  <td className="px-2 py-2">{sourceUrl && <a href={sourceUrl} target="_blank" rel="noreferrer" onClick={(event) => event.stopPropagation()} className="whitespace-nowrap font-semibold text-teal-700 hover:underline">Open in source EHR</a>}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <nav className="mt-1 flex shrink-0 flex-wrap items-center justify-between gap-1.5" aria-label="Table pagination">
        <span className="text-xs text-slate-500">{totalCount === 0 ? "0 patients" : `Showing ${(page - 1) * pageSize + 1}-${Math.min(page * pageSize, totalCount)} of ${totalCount} patients`}</span>
        <div className="flex items-center gap-1.5">
          <label className="flex items-center gap-1.5 text-xs text-slate-600">Rows per page<select value={pageSize} onChange={(event) => onPageSizeChange(Number(event.target.value))} className="rounded border border-slate-300 bg-white px-1.5 py-1 text-xs font-semibold">{[10, 20, 50].map((size) => <option key={size}>{size}</option>)}</select></label>
          <button type="button" onClick={() => onPageChange(page - 1)} disabled={page === 1} className="rounded border border-slate-300 bg-white px-2.5 py-1 text-xs font-semibold disabled:text-slate-400">Previous</button>
          <span className="whitespace-nowrap text-xs text-slate-500">Page {page} of {pages}</span>
          <button type="button" onClick={() => onPageChange(page + 1)} disabled={page >= pages} className="rounded border border-slate-300 bg-white px-2.5 py-1 text-xs font-semibold disabled:text-slate-400">Next</button>
        </div>
      </nav>
    </div>
  );
}
