import { useEffect } from "react";

import { getEpicCallbackUrl } from "../api/ehr";

export function EpicCallbackPage() {
  useEffect(() => {
    window.location.replace(getEpicCallbackUrl(window.location.search));
  }, []);

  return (
    <main className="mx-auto w-full max-w-6xl px-4 py-12 sm:px-6 lg:px-8">
      <p className="rounded-xl border border-slate-200 bg-white px-5 py-10 text-center text-base text-slate-600 shadow-sm">
        Completing Epic authorization...
      </p>
    </main>
  );
}
