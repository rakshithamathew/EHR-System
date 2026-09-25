import type { EhrSource } from "../../types/ehr";

interface EhrSelectorProps {
  ehrs: EhrSource[];
  value: string;
  onChange: (source: string) => void;
}

export function EhrSelector({ ehrs, value, onChange }: EhrSelectorProps) {
  return (
    <fieldset>
      <legend className="sr-only">Choose an EHR source</legend>
      <div
        className="inline-flex max-w-full flex-wrap gap-1 rounded-lg border border-slate-200 bg-slate-50 p-1"
        aria-label="EHR source"
      >
        {ehrs.map((ehr) => {
          const isSelected = ehr.code === value;

          return (
            <button
              key={ehr.code}
              type="button"
              onClick={() => onChange(ehr.code)}
              disabled={!ehr.enabled}
              aria-pressed={isSelected}
              className={`rounded-md border px-4 py-2 text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-teal-600 focus:ring-offset-2 ${
                !ehr.enabled
                  ? "cursor-not-allowed border-transparent bg-transparent text-slate-400"
                  : isSelected
                    ? "border-teal-200 bg-white text-teal-800 shadow-sm"
                    : "border-transparent bg-transparent text-slate-600 hover:bg-white hover:text-slate-900"
              }`}
            >
              {ehr.name}
              {!ehr.enabled && (
                <span className="ml-2 text-xs font-medium">Unavailable</span>
              )}
            </button>
          );
        })}
      </div>
    </fieldset>
  );
}
