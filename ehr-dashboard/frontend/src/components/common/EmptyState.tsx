interface EmptyStateProps {
  message?: string;
}

export function EmptyState({
  message = "No records found.",
}: EmptyStateProps) {
  return (
    <p className="rounded-lg border border-dashed border-slate-300 bg-white px-4 py-10 text-center text-sm text-slate-500">
      {message}
    </p>
  );
}
