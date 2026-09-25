interface LoadingStateProps {
  message?: string;
}

export function LoadingState({
  message = "Loading...",
}: LoadingStateProps) {
  return (
    <div
      className="flex items-center gap-3 rounded-xl border border-slate-200 bg-white px-5 py-8 text-base text-slate-600"
      role="status"
    >
      <span
        className="h-2.5 w-2.5 rounded-full bg-teal-600"
        aria-hidden="true"
      />
      {message}
    </div>
  );
}
