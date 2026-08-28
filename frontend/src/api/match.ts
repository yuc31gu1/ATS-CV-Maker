import type { Importance, RequirementCategory } from "./jobs";

export type MatchStatus = "STRONG_MATCH" | "PARTIAL_MATCH" | "TRANSFERABLE" | "NO_EVIDENCE";

export interface EvidenceMatch {
  requirement: string;
  category: RequirementCategory;
  importance: Importance;
  status: MatchStatus;
  matched_skill: string | null;
  ambiguous: boolean;
  rationale: string;
  evidence_ids: string[];
  evidence: string[];
}

export interface MatchResult {
  job_description_id: string;
  resume_id: string;
  matches: EvidenceMatch[];
  created_at: string;
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api";

async function errorMessage(res: Response, fallback: string): Promise<string> {
  const body = await res.json().catch(() => null);
  return body?.error?.message ?? fallback;
}

export async function fetchMatch(
  jobDescriptionId: string,
  resumeId: string | null,
  signal?: AbortSignal,
): Promise<MatchResult> {
  const query = resumeId ? `?resume_id=${encodeURIComponent(resumeId)}` : "";
  const res = await fetch(
    `${API_BASE_URL}/job-descriptions/${encodeURIComponent(jobDescriptionId)}/match${query}`,
    { signal },
  );
  if (!res.ok) {
    throw new Error(await errorMessage(res, `Match fetch failed with status ${res.status}`));
  }
  return (await res.json()) as MatchResult;
}