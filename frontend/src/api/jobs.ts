export type RequirementCategory =
  | "REQUIRED"
  | "PREFERRED"
  | "RESPONSIBILITY"
  | "SENIORITY"
  | "DOMAIN"
  | "SOFT_SKILL";

export type Importance = "HIGH" | "MEDIUM" | "LOW";

export type JobStatus = "PENDING" | "RUNNING" | "SUCCEEDED" | "FAILED";

export interface JobDescriptionInput {
  company?: string;
  role?: string;
  location?: string;
  jd_text: string;
}

export interface JobDescriptionSubmitResponse {
  job_description_id: string;
  job_id: string;
  status: JobStatus;
}

export interface JobError {
  code: string;
  message: string;
}

export interface JobPayload {
  id: string;
  type: string;
  status: JobStatus;
  result: Record<string, unknown> | null;
  error: JobError | null;
}

export interface JobRequirement {
  requirement: string;
  category: RequirementCategory;
  importance: Importance;
  context: string;
}

export interface JobAnalysis {
  job_description_id: string;
  role: string;
  seniority: string | null;
  requirements: JobRequirement[];
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api";

async function errorMessage(res: Response, fallback: string): Promise<string> {
  const body = await res.json().catch(() => null);
  return body?.error?.message ?? fallback;
}

export async function submitJobDescription(
  input: JobDescriptionInput,
  signal?: AbortSignal,
): Promise<JobDescriptionSubmitResponse> {
  const res = await fetch(`${API_BASE_URL}/job-descriptions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
    signal,
  });
  if (!res.ok) {
    throw new Error(
      await errorMessage(res, `Job description submission failed with status ${res.status}`),
    );
  }
  return (await res.json()) as JobDescriptionSubmitResponse;
}

export async function fetchJob(jobId: string, signal?: AbortSignal): Promise<JobPayload> {
  const res = await fetch(`${API_BASE_URL}/jobs/${jobId}`, { signal });
  if (!res.ok) {
    throw new Error(await errorMessage(res, `Job poll failed with status ${res.status}`));
  }
  return (await res.json()) as JobPayload;
}

export async function fetchJobAnalysis(
  jobDescriptionId: string,
  signal?: AbortSignal,
): Promise<JobAnalysis> {
  const res = await fetch(`${API_BASE_URL}/job-descriptions/${jobDescriptionId}/analysis`, {
    signal,
  });
  if (!res.ok) {
    throw new Error(await errorMessage(res, `Analysis fetch failed with status ${res.status}`));
  }
  return (await res.json()) as JobAnalysis;
}