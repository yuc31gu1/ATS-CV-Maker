export type MonthYear = string;

export interface PersonalInformation {
  full_name: string;
  headline: string;
  email: string;
  phone: string;
  location: string;
  website: string;
}

export interface Experience {
  company: string;
  title: string;
  location: string;
  start_date: MonthYear;
  end_date: MonthYear | null;
  summary: string;
  bullets: string[];
}

export interface Education {
  school: string;
  degree: string;
  field: string;
  location: string;
  start_date: MonthYear;
  end_date: MonthYear | null;
}

export interface Project {
  name: string;
  description: string;
  url: string;
  technologies: string[];
  bullets: string[];
}

export interface Certification {
  name: string;
  issuer: string;
  date: MonthYear;
  url: string;
}

export interface Resume {
  id: string | null;
  schema_version: number;
  personal_information: PersonalInformation;
  summary: string;
  skills: Record<string, string[]>;
  experience: Experience[];
  education: Education[];
  projects: Project[];
  certifications: Certification[];
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

export async function listResumes(signal?: AbortSignal): Promise<Resume[]> {
  const res = await fetch(`${API_BASE_URL}/resumes`, { signal });
  return parseOrThrow<Resume[]>(res);
}

export async function getResume(id: string, signal?: AbortSignal): Promise<Resume> {
  const res = await fetch(`${API_BASE_URL}/resumes/${id}`, { signal });
  return parseOrThrow<Resume>(res);
}

export async function createResume(resume: Resume): Promise<Resume> {
  const res = await fetch(`${API_BASE_URL}/resumes`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(resume),
  });
  return parseOrThrow<Resume>(res);
}

export async function updateResume(id: string, resume: Resume): Promise<Resume> {
  const res = await fetch(`${API_BASE_URL}/resumes/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(resume),
  });
  return parseOrThrow<Resume>(res);
}