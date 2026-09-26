import { type ColumnDef, type OnChangeFn, type SortingState } from "@tanstack/react-table";
import { Link, useNavigate } from "react-router-dom";

import type { PatientSummary } from "../../types/patient";
import {
  ehrSourceBadgeClasses,
  formatDate,
  formatEhrSource,
  getPatientSourceUrl,
} from "../../utils/format";
import { DataTable } from "../common/DataTable";

const patientColumns: ColumnDef<PatientSummary, any>[] = [
  {
    accessorKey: "name",
    header: "Name",
    cell: ({ row }) => {
      const patient = row.original;
      const patientUrl = `/patients/${encodeURIComponent(patient.id)}?source=${encodeURIComponent(patient.source)}`;
      return (
        <Link
          to={patientUrl}
          onClick={(event) => event.stopPropagation()}
          className="rounded-sm font-semibold text-slate-900 outline-none hover:text-teal-800 focus-visible:ring-2 focus-visible:ring-teal-600 focus-visible:ring-offset-2"
        >
          {patient.name || patient.external_id}
        </Link>
      );
    },
  },
  {
    accessorKey: "external_id",
    header: "Patient ID",
    cell: ({ getValue }) => (
      <span className="block max-w-64 truncate font-mono text-xs text-slate-600">
        {String(getValue())}
      </span>
    ),
  },
  {
    accessorKey: "birth_date",
    header: "DOB",
    cell: ({ row }) => (
      <span className="whitespace-nowrap">{formatDate(row.original.birth_date)}</span>
    ),
  },
  {
    accessorKey: "gender",
    header: "Gender",
    cell: ({ getValue }) => (
      <span className="capitalize">{String(getValue() || "Not recorded")}</span>
    ),
  },
  {
    id: "clinical_data",
    header: "Clinical data",
    enableSorting: false,
    cell: ({ row }) => (
      <div className="flex flex-wrap gap-1">
        <span className="inline-flex rounded-full bg-blue-50 px-2 py-0.5 text-[11px] font-semibold text-blue-800 ring-1 ring-inset ring-blue-200">
          {row.original.condition_count} conditions
        </span>
        <span className="inline-flex rounded-full bg-cyan-50 px-2 py-0.5 text-[11px] font-semibold text-cyan-800 ring-1 ring-inset ring-cyan-200">
          {row.original.medication_count} medications
        </span>
      </div>
    ),
  },
  {
    accessorKey: "source",
    header: "EHR Source",
    enableSorting: false,
    cell: ({ row }) => (
      <span
        className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${ehrSourceBadgeClasses(row.original.source)}`}
      >
        {formatEhrSource(row.original.source)}
      </span>
    ),
  },
  {
    id: "source_record",
    header: "Source record",
    enableSorting: false,
    cell: ({ row }) => {
      const patient = row.original;
      const sourceUrl = getPatientSourceUrl(patient.source, patient.external_id);
      return sourceUrl ? (
        <a
          href={sourceUrl}
          target="_blank"
          rel="noreferrer"
          onClick={(event) => event.stopPropagation()}
          className="whitespace-nowrap font-semibold text-teal-700 hover:text-teal-900 hover:underline focus:outline-none focus:ring-2 focus:ring-teal-600 focus:ring-offset-2"
        >
          Open in source EHR
        </a>
      ) : null;
    },
  },
];

interface PatientListProps {
  patients: PatientSummary[];
  sorting: SortingState;
  onSortingChange: OnChangeFn<SortingState>;
  page: number;
  pageSize: number;
  totalCount: number;
  onPageChange: (page: number) => void;
  onPageSizeChange: (pageSize: number) => void;
}

export function PatientList({
  patients,
  sorting,
  onSortingChange,
  page,
  pageSize,
  totalCount,
  onPageChange,
  onPageSizeChange,
}: PatientListProps) {
  const navigate = useNavigate();

  return (
    <DataTable
      columns={patientColumns}
      data={patients}
      sorting={sorting}
      onSortingChange={onSortingChange}
      pageIndex={page - 1}
      pageSize={pageSize}
      totalCount={totalCount}
      onPageChange={(pageIndex) => onPageChange(pageIndex + 1)}
      onPageSizeChange={onPageSizeChange}
      getRowId={(patient) => patient.id}
      onRowClick={(patient) =>
        navigate(
          `/patients/${encodeURIComponent(patient.id)}?source=${encodeURIComponent(patient.source)}`,
        )
      }
      emptyMessage="No patients found."
    />
  );
}
