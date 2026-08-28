import type {
  Certification,
  Education,
  Experience,
  PersonalInformation,
  Project,
} from "./resume";

export type ChangeKind = "SUMMARY" | "BULLET";

export type ChangeStatus = "PENDING" | "ACCEPTED" | "REJECTED" | "EDITED";

export interface TailoredChange {
  key: string;
  kind: ChangeKind;
  section: string;
  original: string;
  tailored: string;
  reason: string;
  source_evidence_ids: string[];
  status: ChangeStatus;
  edited_text: string | null;
}

export interface TailoredResume {
  job_description_id: string;
  resume_version_id: string;
  resume_id: string;
  personal_information: PersonalInformation;
  summary: string;
  skills: Record<string, string[]>;
  experience: Experience[];
  education: Education[];
  projects: Project[];
  certifications: Certification[];
  changes: TailoredChange[];
  created_at: string;
}

export interface TailorSubmitResponse {
  job_id: string;
  job_description_id: string;
  resume_id: string;
  status: string;
}

export type ReviewAction = "accept" | "reject" | "edit";

export interface ReviewDecision {
  key: string;
  action: ReviewAction;
  text?: string;
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

export async function submitTailor(
  resumeId: string,
  jobDescriptionId: string,
  signal?: AbortSignal,
): Promise<TailorSubmitResponse> {
  const res = await fetch(`${API_BASE_URL}/resumes/${encodeURIComponent(resumeId)}/tailor`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ job_description_id: jobDescriptionId }),
    signal,
  });
  return parseOrThrow<TailorSubmitResponse>(res);
}

export async function fetchTailored(
  jobDescriptionId: string,
  signal?: AbortSignal,
): Promise<TailoredResume> {
  const res = await fetch(
    `${API_BASE_URL}/job-descriptions/${encodeURIComponent(jobDescriptionId)}/tailored`,
    { signal },
  );
  return parseOrThrow<TailoredResume>(res);
}

export async function submitReviewDecisions(
  jobDescriptionId: string,
  decisions: ReviewDecision[],
  signal?: AbortSignal,
): Promise<TailoredResume> {
  const res = await fetch(
    `${API_BASE_URL}/job-descriptions/${encodeURIComponent(jobDescriptionId)}/tailored/decisions`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ decisions }),
      signal,
    },
  );
  return parseOrThrow<TailoredResume>(res);
}

export async function submitRegenerate(
  jobDescriptionId: string,
  changeKey: string,
  signal?: AbortSignal,
): Promise<TailorSubmitResponse> {
  const res = await fetch(
    `${API_BASE_URL}/job-descriptions/${encodeURIComponent(jobDescriptionId)}/tailored/regenerate`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ change_key: changeKey }),
      signal,
    },
  );
  return parseOrThrow<TailorSubmitResponse>(res);
}