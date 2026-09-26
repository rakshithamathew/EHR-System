const configuredBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim();
export const apiBaseUrl = configuredBaseUrl?.replace(/\/+$/, "") || window.location.origin;

export class ApiError extends Error {
  constructor(public status: number, public data: { error?: string; detail?: string }) {
    super(data.detail || `Request failed (${status})`);
  }
}

export async function apiRequest<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(new URL(path, apiBaseUrl), {
    ...options,
    credentials: "include",
    headers: { Accept: "application/json", ...options?.headers },
  });
  const data = await response.json();
  if (!response.ok) throw new ApiError(response.status, data);
  return data as T;
}
