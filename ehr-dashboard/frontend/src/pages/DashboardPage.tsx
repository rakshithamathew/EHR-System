import { useEffect, useState } from "react";

import { EmptyState } from "../components/common/EmptyState";
import { ErrorState } from "../components/common/ErrorState";
import { LoadingState } from "../components/common/LoadingState";
import { EhrSelector } from "../components/ehr/EhrSelector";
import { PatientList } from "../components/patients/PatientList";
import {
  useEhrs,
  useEpicConnectionStatus,
  useSyncEhr,
} from "../hooks/useEhrs";
import { usePatients } from "../hooks/usePatients";
import { getEpicLoginUrl } from "../api/ehr";

const PATIENTS_PER_PAGE = 20;
const DASHBOARD_SOURCES = new Set(["hapi", "oracle", "epic"]);

export function DashboardPage() {
  const [selectedEhr, setSelectedEhr] = useState(
    () => new URLSearchParams(window.location.search).get("source") ?? "",
  );
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [page, setPage] = useState(1);
  const ehrsQuery = useEhrs();
  const epicStatusQuery = useEpicConnectionStatus(selectedEhr === "epic");
  const canLoadPatients =
    selectedEhr !== "epic" || epicStatusQuery.data?.connected === true;
  const patientsQuery = usePatients(
    selectedEhr,
    debouncedSearch,
    PATIENTS_PER_PAGE,
    page,
    canLoadPatients,
  );
  const syncMutation = useSyncEhr();

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      setDebouncedSearch(search);
    }, 350);

    return () => window.clearTimeout(timeoutId);
  }, [search]);

  useEffect(() => {
    if (!ehrsQuery.data?.length) {
      return;
    }

    const selectedSource = ehrsQuery.data.find(
      (ehr) =>
        ehr.code === selectedEhr &&
        ehr.enabled &&
        DASHBOARD_SOURCES.has(ehr.code),
    );
    if (selectedSource) {
      return;
    }

    const defaultSource =
      ehrsQuery.data.find((ehr) => ehr.code === "oracle" && ehr.enabled) ??
      ehrsQuery.data.find((ehr) => ehr.code === "hapi" && ehr.enabled) ??
      ehrsQuery.data.find((ehr) => ehr.code === "epic" && ehr.enabled);
    setPage(1);
    setSelectedEhr(defaultSource?.code ?? "");
  }, [ehrsQuery.data, selectedEhr]);

  useEffect(() => {
    if (
      selectedEhr === "epic" &&
      epicStatusQuery.data?.connected === false
    ) {
      window.location.assign(getEpicLoginUrl());
    }
  }, [epicStatusQuery.data?.connected, selectedEhr]);

  function handleSourceChange(source: string) {
    if (source === selectedEhr) {
      return;
    }

    syncMutation.reset();
    setPage(1);
    setSelectedEhr(source);
  }

  function handleSearchChange(value: string) {
    setSearch(value);
    setPage(1);
  }

  const syncResult =
    syncMutation.data?.source === selectedEhr ? syncMutation.data : null;

  return (
    <main className="mx-auto w-full max-w-6xl px-4 py-8 sm:px-6 sm:py-10 lg:px-8">
      <header className="mb-7">
        <h1 className="text-2xl font-semibold tracking-tight text-slate-950 sm:text-3xl">
          Patients
        </h1>
      </header>

      {ehrsQuery.isPending ? (
        <LoadingState message="Loading EHR sources..." />
      ) : ehrsQuery.isError ? (
        <ErrorState error={ehrsQuery.error} />
      ) : ehrsQuery.data.filter(
          (ehr) => DASHBOARD_SOURCES.has(ehr.code),
        ).length === 0 ? (
        <EmptyState message="No EHR sources are configured." />
      ) : (
        <>
          <section className="rounded-xl border border-slate-200 bg-white shadow-sm">
            <div className="border-b border-slate-200 px-5 py-5 sm:px-6">
              <p className="mb-3 text-sm font-semibold text-slate-700">
                EHR source
              </p>
              <EhrSelector
                ehrs={ehrsQuery.data.filter(
                  (ehr) => DASHBOARD_SOURCES.has(ehr.code),
                )}
                value={selectedEhr}
                onChange={handleSourceChange}
              />
            </div>

            <div className="flex flex-col gap-3 px-5 py-5 sm:px-6 md:flex-row">
              <label className="relative flex-1">
                <span className="sr-only">Search patients by name</span>
                <svg
                  aria-hidden="true"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  className="pointer-events-none absolute left-3.5 top-1/2 h-5 w-5 -translate-y-1/2 text-slate-400"
                >
                  <circle cx="11" cy="11" r="7" />
                  <path d="m20 20-4-4" />
                </svg>
                <input
                  type="search"
                  value={search}
                  onChange={(event) => handleSearchChange(event.target.value)}
                  disabled={!selectedEhr}
                  placeholder="Search by patient name"
                  className="w-full rounded-lg border border-slate-300 bg-white py-2.5 pl-11 pr-3 text-base text-slate-900 outline-none placeholder:text-slate-400 focus:border-teal-600 focus:ring-2 focus:ring-teal-100 disabled:bg-slate-100"
                />
              </label>

              {selectedEhr === "epic" ? (
                <a
                  href={getEpicLoginUrl()}
                  className="rounded-lg bg-teal-700 px-5 py-2.5 text-center text-sm font-semibold text-white hover:bg-teal-800 focus:outline-none focus:ring-2 focus:ring-teal-600 focus:ring-offset-2"
                >
                  {epicStatusQuery.data?.connected
                    ? "Reconnect Epic"
                    : "Connect Epic"}
                </a>
              ) : (
                <button
                  type="button"
                  onClick={() => syncMutation.mutate(selectedEhr)}
                  disabled={!selectedEhr || syncMutation.isPending}
                  aria-busy={syncMutation.isPending}
                  className="rounded-lg bg-teal-700 px-5 py-2.5 text-sm font-semibold text-white hover:bg-teal-800 focus:outline-none focus:ring-2 focus:ring-teal-600 focus:ring-offset-2 disabled:cursor-not-allowed disabled:bg-slate-300"
                >
                  {syncMutation.isPending ? "Syncing data..." : "Sync Data"}
                </button>
              )}
            </div>
          </section>

          <div className="mt-4" aria-live="polite">
            {syncMutation.isError && <ErrorState error={syncMutation.error} />}
            {syncResult && (
              <p className="rounded-xl border border-teal-200 bg-teal-50 px-5 py-4 text-base text-teal-900">
                Sync complete: {syncResult.patients_processed} patients, {" "}
                {syncResult.conditions_processed} conditions, and {" "}
                {syncResult.medications_processed} medications processed.
              </p>
            )}
          </div>

          <section className="mt-8" aria-labelledby="patient-list-heading">
            <div className="mb-4 flex items-baseline justify-between gap-4">
              <h2
                id="patient-list-heading"
                className="text-xl font-semibold text-slate-950"
              >
                Patient directory
              </h2>
              {patientsQuery.data && (
                <span className="hidden text-sm font-medium text-slate-500 sm:inline">
                  Page {page}
                </span>
              )}
            </div>

            {!selectedEhr ? (
              <EmptyState message="Select an EHR source to view patients." />
            ) : selectedEhr === "epic" && epicStatusQuery.isPending ? (
              <LoadingState message="Checking Epic connection..." />
            ) : selectedEhr === "epic" && epicStatusQuery.isError ? (
              <ErrorState error={epicStatusQuery.error} />
            ) : selectedEhr === "epic" &&
              epicStatusQuery.data?.connected !== true ? (
              <EmptyState message="Connect Epic to load sandbox patients." />
            ) : patientsQuery.isPending ? (
              <LoadingState message="Loading patients..." />
            ) : patientsQuery.isError ? (
              <ErrorState error={patientsQuery.error} />
            ) : (
              <>
                <PatientList patients={patientsQuery.data.items} />
                <nav
                  className="mt-5 flex items-center justify-between gap-4 sm:justify-end"
                  aria-label="Patient list pagination"
                >
                  <button
                    type="button"
                    onClick={() => setPage((current) => Math.max(1, current - 1))}
                    disabled={page === 1}
                    className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-teal-600 focus:ring-offset-2 disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-400"
                  >
                    Previous
                  </button>
                  <span className="text-sm text-slate-500 sm:hidden">
                    Page {page}
                  </span>
                  <button
                    type="button"
                    onClick={() => setPage((current) => current + 1)}
                    disabled={!patientsQuery.data.has_next}
                    className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-teal-600 focus:ring-offset-2 disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-400"
                  >
                    Next
                  </button>
                </nav>
              </>
            )}
          </section>
        </>
      )}
    </main>
  );
}
