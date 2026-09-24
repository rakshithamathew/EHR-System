import { useEffect, useState } from "react";

import { EmptyState } from "../components/common/EmptyState";
import { ErrorState } from "../components/common/ErrorState";
import { LoadingState } from "../components/common/LoadingState";
import { EhrSelector } from "../components/ehr/EhrSelector";
import { PatientList } from "../components/patients/PatientList";
import { useEhrs, useSyncEhr } from "../hooks/useEhrs";
import { usePatients } from "../hooks/usePatients";

export function DashboardPage() {
  const [selectedEhr, setSelectedEhr] = useState("");
  const [search, setSearch] = useState("");
  const ehrsQuery = useEhrs();
  const patientsQuery = usePatients(selectedEhr, search);
  const syncMutation = useSyncEhr();

  useEffect(() => {
    if (!ehrsQuery.data?.length) {
      return;
    }

    const selectedSource = ehrsQuery.data.find(
      (ehr) => ehr.code === selectedEhr && ehr.enabled,
    );
    if (selectedSource) {
      return;
    }

    const defaultSource =
      ehrsQuery.data.find((ehr) => ehr.code === "hapi" && ehr.enabled) ??
      ehrsQuery.data.find((ehr) => ehr.enabled);
    setSelectedEhr(defaultSource?.code ?? "");
  }, [ehrsQuery.data, selectedEhr]);

  function handleSourceChange(source: string) {
    if (source === selectedEhr) {
      return;
    }

    syncMutation.reset();
    setSelectedEhr(source);
  }

  const syncResult =
    syncMutation.data?.source === selectedEhr ? syncMutation.data : null;

  return (
    <main className="mx-auto w-full max-w-5xl px-4 py-10 sm:px-6 lg:px-8">
      <header className="mb-8">
        <p className="mb-2 text-sm font-medium text-blue-700">Clinical data browser</p>
        <h1 className="text-3xl font-semibold tracking-tight text-slate-950">
          EHR Patient Dashboard
        </h1>
      </header>

      {ehrsQuery.isPending ? (
        <LoadingState message="Loading EHR sources..." />
      ) : ehrsQuery.isError ? (
        <ErrorState error={ehrsQuery.error} />
      ) : ehrsQuery.data.length === 0 ? (
        <EmptyState message="No EHR sources are configured." />
      ) : (
        <>
          <EhrSelector
            ehrs={ehrsQuery.data}
            value={selectedEhr}
            onChange={handleSourceChange}
          />

          <div className="my-6 flex flex-col gap-3 sm:flex-row">
            <button
              type="button"
              onClick={() => syncMutation.mutate(selectedEhr)}
              disabled={!selectedEhr || syncMutation.isPending}
              className="rounded-md bg-blue-700 px-4 py-2.5 text-sm font-semibold text-white hover:bg-blue-800 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:ring-offset-2 disabled:cursor-not-allowed disabled:bg-slate-300"
            >
              {syncMutation.isPending ? "Syncing data..." : "Sync Data"}
            </button>

            <label className="relative flex-1">
              <span className="sr-only">Search patients</span>
              <input
                type="search"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                disabled={!selectedEhr}
                placeholder="Search patients..."
                className="w-full rounded-md border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-900 outline-none placeholder:text-slate-400 focus:border-blue-600 focus:ring-1 focus:ring-blue-600 disabled:bg-slate-100"
              />
            </label>
          </div>

          <div className="mb-6" aria-live="polite">
            {syncMutation.isError && <ErrorState error={syncMutation.error} />}
            {syncResult && (
              <p className="rounded-md border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
                Sync complete: {syncResult.patients_processed} patients, {" "}
                {syncResult.conditions_processed} conditions, and {" "}
                {syncResult.medications_processed} medications processed.
              </p>
            )}
          </div>

          <section aria-labelledby="patient-list-heading">
            <div className="mb-3 flex items-baseline justify-between gap-4">
              <h2
                id="patient-list-heading"
                className="text-lg font-semibold text-slate-900"
              >
                Patient list
              </h2>
              {patientsQuery.data && (
                <span className="text-sm text-slate-500">
                  {patientsQuery.data.length} {" "}
                  {patientsQuery.data.length === 1 ? "patient" : "patients"}
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
              <PatientList patients={patientsQuery.data} />
            )}
          </section>
        </>
      )}
    </main>
  );
}
