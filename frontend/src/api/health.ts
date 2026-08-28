export type DatabaseStatus = "ok" | "unavailable";

export interface HealthResponse {
  status: string;
  service: string;
  database: { status: DatabaseStatus };
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api";

export async function fetchHealth(signal?: AbortSignal): Promise<HealthResponse> {
  const res = await fetch(`${API_BASE_URL}/health`, { signal });
  if (!res.ok) {
    throw new Error(`Health check failed with status ${res.status}`);
  }
  return (await res.json()) as HealthResponse;
}