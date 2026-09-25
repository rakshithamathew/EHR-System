export function formatDate(value: string | null): string {
  if (!value) {
    return "Not recorded";
  }

  const [year, month, day] = value.slice(0, 10).split("-").map(Number);
  if (!year || !month || !day) {
    return value;
  }

  return new Intl.DateTimeFormat(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    timeZone: "UTC",
  }).format(new Date(Date.UTC(year, month - 1, day)));
}

export function formatEhrSource(source: string): string {
  const sourceNames: Record<string, string> = {
    hapi: "HAPI FHIR",
    oracle: "Oracle Health",
    epic: "Epic",
  };

  return sourceNames[source.toLowerCase()] ?? source;
}
