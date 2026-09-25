interface EmptyStateProps {
  message?: string;
}

export function EmptyState({
  message = "No records found.",
}: EmptyStateProps) {
  return (
    <p className="rounded-xl border border-dashed border-slate-300 bg-slate-50/60 px-5 py-12 text-center text-base text-slate-600">
      {message}
    </p>
  );
}
