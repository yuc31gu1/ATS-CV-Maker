export type DatabaseStatus = "ok" | "unavailable";

export interface HealthResponse {
  status: string;
  service: string;
  database: { status: DatabaseStatus };
}

export async function fetchHealth(signal?: AbortSignal): Promise<HealthResponse> {
  const res = await fetch("/api/health", { signal });
  if (!res.ok) {
    throw new Error(`Health check failed with status ${res.status}`);
  }
  return (await res.json()) as HealthResponse;
}