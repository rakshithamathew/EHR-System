interface LoadingStateProps {
  message?: string;
}

export function LoadingState({
  message = "Loading...",
}: LoadingStateProps) {
  return (
    <p className="py-8 text-sm text-slate-500" role="status">
      {message}
    </p>
  );
}
