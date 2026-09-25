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

export function formatDateTime(value: string | null): string {
  if (!value) {
    return "Never";
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(parsed);
}

export function ehrSourceBadgeClasses(source: string): string {
  const classes: Record<string, string> = {
    hapi: "bg-blue-50 text-blue-800 ring-blue-200",
    oracle: "bg-red-50 text-red-800 ring-red-200",
    epic: "bg-orange-50 text-orange-800 ring-orange-200",
  };

  return classes[source.toLowerCase()] ?? "bg-slate-50 text-slate-700 ring-slate-200";
}

export function getPatientSourceUrl(source: string, patientId: string): string | null {
  const baseUrls: Record<string, string> = {
    hapi: "https://hapi.fhir.org/baseR4/Patient/",
    oracle:
      "https://fhir-open.cerner.com/r4/ec2458f2-1e24-41c8-b71b-0e701af7583d/Patient/",
    epic: "https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4/Patient/",
  };
  const baseUrl = baseUrls[source.toLowerCase()];
  return baseUrl ? `${baseUrl}${encodeURIComponent(patientId)}` : null;
}
