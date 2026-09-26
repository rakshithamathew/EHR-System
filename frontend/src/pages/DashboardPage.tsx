import { useEffect, useRef, useState } from "react";
import { EmptyState, ErrorState, LoadingState } from "../components/Status";
import { EhrSelector } from "../components/EhrSelector";
import { PatientList, type PatientSort } from "../components/PatientList";
import {
  getEpicLoginUrl,
  useDisconnectEpic,
  useEhrs,
  useEpicConnectionStatus,
  useSyncEhr,
} from "../api/ehr";
import { usePatients } from "../api/patients";

const DASHBOARD_SOURCES = new Set(["hapi", "oracle", "epic"]);

export function DashboardPage() {
  const handledEpicCallback = useRef(false);
  const [selectedEhr, setSelectedEhr] = useState(
    () => new URLSearchParams(window.location.search).get("source") ?? "",
  );
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [sort, setSort] = useState<PatientSort>({ id: "name", desc: false });
  const ehrsQuery = useEhrs();
  const patientsQuery = usePatients(
    selectedEhr,
    debouncedSearch,
    pageSize,
    page,
    sort.id,
    sort.desc ? "desc" : "asc",
    true,
  );
  const syncMutation = useSyncEhr();
  const epicConnectionQuery = useEpicConnectionStatus(selectedEhr === "epic");
  const disconnectEpicMutation = useDisconnectEpic();

  useEffect(() => {
    const searchParams = new URLSearchParams(window.location.search);
    if (
      handledEpicCallback.current ||
      selectedEhr !== "epic" ||
      searchParams.get("epic") !== "connected"
    ) {
      return;
    }

    handledEpicCallback.current = true;
    searchParams.delete("epic");
    const nextSearch = searchParams.toString();
    window.history.replaceState(
      null,
      "",
      `${window.location.pathname}${nextSearch ? `?${nextSearch}` : ""}${window.location.hash}`,
    );
    syncMutation.mutate("epic");
  }, [selectedEhr, syncMutation]);

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      setDebouncedSearch(search);
    }, 350);

    return () => window.clearTimeout(timeoutId);
  }, [search]);

  useEffect(() => {
    if (!selectedEhr) {
      return;
    }

    const searchParams = new URLSearchParams(window.location.search);
    if (searchParams.get("source") === selectedEhr) {
      return;
    }

    searchParams.set("source", selectedEhr);
    window.history.replaceState(
      null,
      "",
      `${window.location.pathname}?${searchParams.toString()}${window.location.hash}`,
    );
  }, [selectedEhr]);

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
      ehrsQuery.data.find((ehr) => ehr.code === "hapi" && ehr.enabled);
    setPage(1);
    setSelectedEhr(defaultSource?.code ?? "");
  }, [ehrsQuery.data, selectedEhr]);

  function handleSourceChange(source: string) {
    if (source === selectedEhr) {
      return;
    }

    syncMutation.reset();
    disconnectEpicMutation.reset();
    setPage(1);
    setSelectedEhr(source);
  }

  function handleSearchChange(value: string) {
    setSearch(value);
    setPage(1);
  }

  function handleSort(nextSort: PatientSort) {
    setSort(nextSort);
    setPage(1);
  }

  function handlePageSizeChange(nextPageSize: number) {
    setPage(1);
    setPageSize(nextPageSize);
  }

  const syncResult =
    syncMutation.data?.source === selectedEhr ? syncMutation.data : null;

  return (
    <main className="flex h-full w-full min-h-0 flex-col overflow-hidden p-[3px]">
      <header className="mb-1 shrink-0">
        <h1 className="text-lg font-semibold tracking-tight text-slate-950">
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
          <section className="flex shrink-0 flex-col rounded-md border border-slate-200 bg-white shadow-sm md:flex-row md:items-center">
            <div className="flex shrink-0 items-center gap-2 border-b border-slate-200 px-2 py-1.5 md:border-b-0 md:border-r">
              <p className="whitespace-nowrap text-xs font-semibold text-slate-700">
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

            <div className="flex min-w-0 flex-1 flex-col gap-1.5 px-2 py-1.5 md:flex-row">
              <label className="relative flex-1">
                <span className="sr-only">Search patients by name</span>
                <svg
                  aria-hidden="true"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400"
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
                  className="w-full rounded-md border border-slate-300 bg-white py-1.5 pl-9 pr-2 text-sm text-slate-900 outline-none placeholder:text-slate-400 focus:border-teal-600 focus:ring-2 focus:ring-teal-100 disabled:bg-slate-100"
                />
              </label>

              <button
                type="button"
                onClick={() => syncMutation.mutate(selectedEhr)}
                disabled={!selectedEhr || syncMutation.isPending}
                aria-busy={syncMutation.isPending}
                className="inline-flex min-w-24 items-center justify-center gap-1.5 rounded-md bg-teal-700 px-3 py-1.5 text-xs font-semibold text-white hover:bg-teal-800 focus:outline-none focus:ring-2 focus:ring-teal-600 focus:ring-offset-2 disabled:cursor-not-allowed disabled:bg-slate-300"
              >
                {syncMutation.isPending && (
                  <span
                    aria-hidden="true"
                    className="h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white"
                  />
                )}
                {syncMutation.isPending ? "Syncing data..." : "Sync Data"}
              </button>

              {selectedEhr === "epic" &&
                !epicConnectionQuery.isPending &&
                (epicConnectionQuery.data?.connected ? (
                  <button
                    type="button"
                    onClick={() => disconnectEpicMutation.mutate()}
                    disabled={disconnectEpicMutation.isPending}
                    className="inline-flex min-w-24 items-center justify-center rounded-md border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:text-slate-400"
                  >
                    {disconnectEpicMutation.isPending
                      ? "Disconnecting..."
                      : "Disconnect Epic"}
                  </button>
                ) : (
                  <a
                    href={getEpicLoginUrl()}
                    className="inline-flex min-w-24 items-center justify-center rounded-md border border-teal-700 bg-white px-3 py-1.5 text-xs font-semibold text-teal-800 hover:bg-teal-50"
                  >
                    Connect Epic
                  </a>
                ))}
            </div>
          </section>

          {disconnectEpicMutation.isError && (
            <div className="mt-1 shrink-0" aria-live="polite">
              <ErrorState error={disconnectEpicMutation.error} />
            </div>
          )}

          {syncMutation.isError && (
            <div className="mt-1 shrink-0" aria-live="polite">
              <ErrorState error={syncMutation.error} />
            </div>
          )}

          {syncResult && (
            <div
              role="status"
              className="fixed right-4 top-4 z-50 max-w-md rounded-lg border border-teal-200 bg-white px-4 py-2.5 text-xs font-medium text-teal-950 shadow-lg sm:right-6 sm:top-6"
            >
              Synced {syncResult.patients_processed} patients, {syncResult.conditions_processed}{" "}
              conditions, {syncResult.medications_processed} medications
              <button
                type="button"
                onClick={() => syncMutation.reset()}
                className="ml-3 text-teal-700 underline hover:text-teal-900"
              >
                Dismiss
              </button>
            </div>
          )}

          <section
            className="mt-1 flex min-h-0 flex-1 flex-col"
            aria-labelledby="patient-list-heading"
          >
            <div className="mb-1 flex shrink-0 items-baseline justify-between gap-2">
              <h2
                id="patient-list-heading"
                className="text-sm font-semibold text-slate-950"
              >
                Patient directory
              </h2>
              {patientsQuery.data && (
                <span className="hidden text-xs font-medium text-slate-500 sm:inline">
                  {patientsQuery.data.total} total patients
                </span>
              )}
            </div>

            {!selectedEhr ? (
              <EmptyState message="Select an EHR source to view patients." />
            ) : patientsQuery.isPending ? (
              <LoadingState message="Loading patients..." />
            ) : patientsQuery.isError ? (
              <ErrorState error={patientsQuery.error} />
            ) : (
              <PatientList
                patients={patientsQuery.data.items}
                sort={sort}
                onSort={handleSort}
                page={page}
                pageSize={pageSize}
                totalCount={patientsQuery.data.total}
                onPageChange={setPage}
                onPageSizeChange={handlePageSizeChange}
              />
            )}
          </section>
        </>
      )}
    </main>
  );
}
