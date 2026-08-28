export interface AtsAnalysis {
  required_keyword_coverage: number | null;
  preferred_keyword_coverage: number | null;
  evidence_coverage: number | null;
  pdf_text_extraction: boolean;
  single_column: boolean;
  standard_headings: boolean;
  critical_info_in_body: boolean;
  unexpected_tables: number;
  unexpected_graphics: number;
  page_count: number;
  warnings: string[];
  unsupported_requirements: string[];
}

export interface GeneratedResume {
  job_description_id: string;
  resume_version_id: string;
  resume_id: string;
  latex_key: string;
  pdf_key: string;
  created_at: string;
  ats_analysis: AtsAnalysis | null;
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

async function blobOrThrow(res: Response): Promise<Blob> {
  if (!res.ok) {
    await parseOrThrow<unknown>(res);
  }
  return await res.blob();
}

async function objectUrlOrThrow(res: Response): Promise<string> {
  const blob = await blobOrThrow(res);
  return URL.createObjectURL(blob);
}

export async function fetchGenerated(
  jobDescriptionId: string,
  signal?: AbortSignal,
): Promise<GeneratedResume> {
  const res = await fetch(
    `${API_BASE_URL}/job-descriptions/${encodeURIComponent(jobDescriptionId)}/generated`,
    { signal },
  );
  return parseOrThrow<GeneratedResume>(res);
}

export async function generateDocument(
  jobDescriptionId: string,
  signal?: AbortSignal,
): Promise<GeneratedResume> {
  const res = await fetch(
    `${API_BASE_URL}/job-descriptions/${encodeURIComponent(jobDescriptionId)}/generated`,
    { method: "POST", signal },
  );
  return parseOrThrow<GeneratedResume>(res);
}

export async function fetchAnalysis(
  jobDescriptionId: string,
  signal?: AbortSignal,
): Promise<AtsAnalysis> {
  const res = await fetch(
    `${API_BASE_URL}/job-descriptions/${encodeURIComponent(jobDescriptionId)}/generated/analysis`,
    { signal },
  );
  return parseOrThrow<AtsAnalysis>(res);
}

export async function generatedPdfUrl(
  jobDescriptionId: string,
  signal?: AbortSignal,
): Promise<string> {
  const res = await fetch(
    `${API_BASE_URL}/job-descriptions/${encodeURIComponent(jobDescriptionId)}/generated/pdf`,
    { signal },
  );
  return objectUrlOrThrow(res);
}

export async function generatedLatexUrl(
  jobDescriptionId: string,
  signal?: AbortSignal,
): Promise<string> {
  const res = await fetch(
    `${API_BASE_URL}/job-descriptions/${encodeURIComponent(jobDescriptionId)}/generated/latex`,
    { signal },
  );
  return objectUrlOrThrow(res);
}