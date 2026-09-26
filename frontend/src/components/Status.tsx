export function EmptyState({ message = "No records found." }: { message?: string }) {
  return <p className="rounded-lg border border-dashed border-slate-300 bg-slate-50/60 px-4 py-6 text-center text-sm text-slate-600">{message}</p>;
}

export function ErrorState({ error }: { error: unknown }) {
  return <p className="rounded-lg border border-red-200 bg-red-50 px-4 py-2.5 text-sm text-red-800" role="alert">{error instanceof Error ? error.message : "Something went wrong."}</p>;
}

export function LoadingState({ message = "Loading..." }: { message?: string }) {
  return <div className="flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-4 py-4 text-sm text-slate-600" role="status"><span className="h-2 w-2 rounded-full bg-teal-600" aria-hidden="true" />{message}</div>;
}
