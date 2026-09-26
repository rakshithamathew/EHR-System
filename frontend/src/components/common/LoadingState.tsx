interface LoadingStateProps {
  message?: string;
}

export function LoadingState({
  message = "Loading...",
}: LoadingStateProps) {
  return (
    <div
      className="flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-4 py-4 text-sm text-slate-600"
      role="status"
    >
      <span
        className="h-2 w-2 rounded-full bg-teal-600"
        aria-hidden="true"
      />
      {message}
    </div>
  );
}
