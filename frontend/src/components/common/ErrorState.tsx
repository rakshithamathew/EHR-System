interface ErrorStateProps {
  error: unknown;
}

export function ErrorState({ error }: ErrorStateProps) {
  const message = error instanceof Error ? error.message : "Something went wrong.";
  return (
    <p
      className="rounded-xl border border-red-200 bg-red-50 px-5 py-4 text-base text-red-800"
      role="alert"
    >
      {message}
    </p>
  );
}
