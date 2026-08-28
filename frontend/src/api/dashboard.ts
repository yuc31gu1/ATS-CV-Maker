import type { Resume } from "./resume";

export interface ApplicationSummary {
  job_description_id: string;
  company: string | null;
  role: string | null;
  location: string | null;
  created_at: string;
  has_analysis: boolean;
  has_tailored: boolean;
  has_generated: boolean;
}

export interface DashboardSummary {
  master_resume: Resume | null;
  tailored_cv_count: number;
  analyzed_jobs_count: number;
  recent_applications: ApplicationSummary[];
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api";

async function parseOrThrow<T>(res: Response): Promise<T> {
  if (res.ok) {
    return (await res.json()) as T;
  }
  let message = `Request failed with status ${res.status}`;
  try {
    const body = (await res.json()) as { error?: { code?: string; message?: string } };
    if (body.error?.message) {
      message = body.error.message;
    }
  } catch {
    // non-JSON error body; keep the status-based message
  }
  throw new Error(message);
}

export async function fetchDashboard(signal?: AbortSignal): Promise<DashboardSummary> {
  const res = await fetch(`${API_BASE_URL}/dashboard`, { signal });
  return parseOrThrow<DashboardSummary>(res);
}

export async function fetchApplications(signal?: AbortSignal): Promise<ApplicationSummary[]> {
  const res = await fetch(`${API_BASE_URL}/applications`, { signal });
  return parseOrThrow<ApplicationSummary[]>(res);
}