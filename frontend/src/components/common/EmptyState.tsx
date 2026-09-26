interface EmptyStateProps {
  message?: string;
}

export function EmptyState({
  message = "No records found.",
}: EmptyStateProps) {
  return (
    <p className="rounded-lg border border-dashed border-slate-300 bg-slate-50/60 px-4 py-6 text-center text-sm text-slate-600">
      {message}
    </p>
  );
}
