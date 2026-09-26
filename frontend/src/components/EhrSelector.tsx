import type { EhrSource } from "../types";

export function EhrSelector({ ehrs, value, onChange }: { ehrs: EhrSource[]; value: string; onChange: (source: string) => void }) {
  return <fieldset><legend className="sr-only">Choose an EHR source</legend><div className="inline-flex max-w-full flex-wrap gap-0.5 rounded border border-slate-200 bg-slate-50 p-0.5" aria-label="EHR source">{ehrs.map((ehr) => {
    const selected = ehr.code === value;
    return <button key={ehr.code} type="button" onClick={() => onChange(ehr.code)} disabled={!ehr.enabled} aria-pressed={selected} className={`rounded border px-2 py-1 text-left text-xs font-semibold focus:outline-none focus:ring-2 focus:ring-teal-600 ${!ehr.enabled ? "cursor-not-allowed border-transparent text-slate-400" : selected ? "border-teal-200 bg-white text-teal-800 shadow-sm" : "border-transparent text-slate-600 hover:bg-white"}`}>{ehr.name}{!ehr.enabled && <span className="ml-2 text-xs font-medium">Unavailable</span>}</button>;
  })}</div></fieldset>;
}
