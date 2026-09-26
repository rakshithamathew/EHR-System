interface ErrorStateProps {
  error: unknown;
}

export function ErrorState({ error }: ErrorStateProps) {
  const message = error instanceof Error ? error.message : "Something went wrong.";
  return (
    <p
      className="rounded-lg border border-red-200 bg-red-50 px-4 py-2.5 text-sm text-red-800"
      role="alert"
    >
      {message}
    </p>
  );
}
