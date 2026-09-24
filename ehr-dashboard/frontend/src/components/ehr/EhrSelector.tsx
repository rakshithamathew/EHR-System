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
      <div className="flex flex-wrap gap-2" aria-label="EHR source">
        {ehrs.map((ehr) => {
          const isSelected = ehr.code === value;

          return (
            <button
              key={ehr.code}
              type="button"
              onClick={() => onChange(ehr.code)}
              disabled={!ehr.enabled}
              aria-pressed={isSelected}
              className={`rounded-md border px-4 py-2 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-blue-600 focus:ring-offset-2 ${
                !ehr.enabled
                  ? "cursor-not-allowed border-slate-200 bg-slate-100 text-slate-400"
                  : isSelected
                    ? "border-blue-700 bg-blue-700 text-white"
                    : "border-slate-300 bg-white text-slate-700 hover:border-slate-400"
              }`}
            >
              {ehr.name}
              {!ehr.enabled && (
                <span className="ml-2 text-xs font-normal">Unavailable</span>
              )}
            </button>
          );
        })}
      </div>
    </fieldset>
  );
}
