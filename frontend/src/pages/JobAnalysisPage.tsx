import { useEffect, useState, type FormEvent } from "react";
import {
  fetchJob,
  fetchJobAnalysis,
  submitJobDescription,
  type JobAnalysis,
  type JobRequirement,
  type RequirementCategory,
} from "../api/jobs";

type Phase =
  | { name: "form" }
  | { name: "submitting" }
  | { name: "analyzing"; jobDescriptionId: string; jobId: string }
  | { name: "done"; analysis: JobAnalysis }
  | { name: "error"; message: string };

const POLL_INTERVAL_MS = 800;

function RequirementList({
  title,
  requirements,
}: {
  title: string;
  requirements: JobRequirement[];
}) {
  if (requirements.length === 0) {
    return null;
  }
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500">{title}</h3>
      <ul className="mt-3 space-y-2">
        {requirements.map((requirement) => (
          <li key={`${requirement.category}:${requirement.requirement}`} className="flex items-start gap-2">
            <span className="text-sm text-slate-700">{requirement.requirement}</span>
            <span className="ml-auto shrink-0 rounded-full bg-indigo-50 px-2 py-0.5 text-xs font-medium text-indigo-700">
              {requirement.importance}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}

const inputClass =
  "mt-1 block w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500";

export function JobAnalysisPage() {
  const [phase, setPhase] = useState<Phase>({ name: "form" });
  const [company, setCompany] = useState("");
  const [role, setRole] = useState("");
  const [location, setLocation] = useState("");
  const [jdText, setJdText] = useState("");

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!jdText.trim()) {
      return;
    }
    setPhase({ name: "submitting" });
    try {
      const submitted = await submitJobDescription({
        company,
        role,
        location,
        jd_text: jdText,
      });
      setPhase({
        name: "analyzing",
        jobDescriptionId: submitted.job_description_id,
        jobId: submitted.job_id,
      });
    } catch (err) {
      setPhase({ name: "error", message: err instanceof Error ? err.message : String(err) });
    }
  }

  useEffect(() => {
    if (phase.name !== "analyzing") {
      return;
    }
    const { jobDescriptionId, jobId } = phase;
    const controller = new AbortController();
    async function tick() {
      try {
        const job = await fetchJob(jobId, controller.signal);
        if (job.status === "SUCCEEDED") {
          const analysis = await fetchJobAnalysis(jobDescriptionId, controller.signal);
          setPhase({ name: "done", analysis });
        } else if (job.status === "FAILED") {
          setPhase({ name: "error", message: job.error?.message ?? "Job analysis failed" });
        }
      } catch (err) {
        if (controller.signal.aborted) {
          return;
        }
        setPhase({ name: "error", message: err instanceof Error ? err.message : String(err) });
      }
    }
    void tick();
    const interval = window.setInterval(() => void tick(), POLL_INTERVAL_MS);
    return () => {
      window.clearInterval(interval);
      controller.abort();
    };
  }, [phase]);

  const requirementsOf = (category: RequirementCategory): JobRequirement[] =>
    phase.name === "done"
      ? phase.analysis.requirements.filter((requirement) => requirement.category === category)
      : [];

  return (
    <main className="min-h-screen bg-slate-50">
      <div className="mx-auto max-w-2xl px-4 py-10">
        <h1 className="text-xl font-semibold text-slate-900">Job Analysis</h1>
        <p className="mt-1 text-sm text-slate-500">
          Paste a Job Description to extract the role, required skills, preferred skills, and
          responsibilities.
        </p>

        {phase.name === "form" && (
          <form onSubmit={handleSubmit} className="mt-6 space-y-4">
            <div className="grid grid-cols-3 gap-3">
              <label className="block text-sm text-slate-600">
                Company
                <input
                  className={inputClass}
                  value={company}
                  onChange={(event) => setCompany(event.target.value)}
                />
              </label>
              <label className="block text-sm text-slate-600">
                Role
                <input
                  className={inputClass}
                  value={role}
                  onChange={(event) => setRole(event.target.value)}
                />
              </label>
              <label className="block text-sm text-slate-600">
                Location
                <input
                  className={inputClass}
                  value={location}
                  onChange={(event) => setLocation(event.target.value)}
                />
              </label>
            </div>
            <label className="block text-sm text-slate-600">
              Job Description
              <textarea
                className={inputClass}
                rows={10}
                placeholder="Paste the full job description here…"
                value={jdText}
                onChange={(event) => setJdText(event.target.value)}
              />
            </label>
            <button
              type="submit"
              disabled={!jdText.trim()}
              className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-700 disabled:cursor-not-allowed disabled:bg-slate-300"
            >
              Analyze
            </button>
          </form>
        )}

        {phase.name === "submitting" && (
          <p className="mt-6 text-sm text-slate-500">Submitting job description…</p>
        )}

        {phase.name === "analyzing" && (
          <div className="mt-6 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex items-center gap-3">
              <span className="h-2 w-2 animate-pulse rounded-full bg-indigo-500" />
              <p className="text-sm text-slate-600">
                Analyzing job description… this can take a moment.
              </p>
            </div>
          </div>
        )}

        {phase.name === "done" && (
          <div className="mt-6 space-y-4">
            <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
              <h2 className="text-lg font-semibold text-slate-900">{phase.analysis.role}</h2>
              {phase.analysis.seniority && (
                <p className="mt-1 text-sm text-slate-500">Seniority: {phase.analysis.seniority}</p>
              )}
            </div>
            <RequirementList title="Required skills" requirements={requirementsOf("REQUIRED")} />
            <RequirementList title="Preferred skills" requirements={requirementsOf("PREFERRED")} />
            <RequirementList
              title="Responsibilities"
              requirements={requirementsOf("RESPONSIBILITY")}
            />
            <RequirementList title="Seniority signals" requirements={requirementsOf("SENIORITY")} />
            <RequirementList
              title="Domain & soft skills"
              requirements={[...requirementsOf("DOMAIN"), ...requirementsOf("SOFT_SKILL")]}
            />
          </div>
        )}

        {phase.name === "error" && <p className="mt-6 text-sm text-red-600">{phase.message}</p>}
      </div>
    </main>
  );
}