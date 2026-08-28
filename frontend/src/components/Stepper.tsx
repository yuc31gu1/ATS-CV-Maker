import { Link } from "react-router-dom";

export type StepKey =
  | "master-cv"
  | "job"
  | "analysis"
  | "match"
  | "generate"
  | "review"
  | "ats"
  | "export";

const STEPS: { key: StepKey; label: string }[] = [
  { key: "master-cv", label: "Master CV" },
  { key: "job", label: "Job" },
  { key: "analysis", label: "Analysis" },
  { key: "match", label: "Match" },
  { key: "generate", label: "Generate" },
  { key: "review", label: "Review" },
  { key: "ats", label: "ATS" },
  { key: "export", label: "Export" },
];

function hrefFor(step: StepKey, jobDescriptionId: string | null): string | null {
  switch (step) {
    case "master-cv":
      return "/resume";
    case "job":
      return "/create/job-analysis";
    case "analysis":
      return jobDescriptionId
        ? `/create/job-analysis?jd=${jobDescriptionId}`
        : "/create/job-analysis";
    case "match":
      return jobDescriptionId ? `/create/match?jd=${jobDescriptionId}` : null;
    case "generate":
    case "review":
      return jobDescriptionId ? `/create/review?jd=${jobDescriptionId}` : null;
    case "ats":
    case "export":
      return jobDescriptionId ? `/create/result?jd=${jobDescriptionId}` : null;
  }
}

function stepClass(active: boolean, reached: boolean): string {
  if (active) {
    return "rounded-full bg-indigo-600 px-2.5 py-1 text-xs font-medium text-white";
  }
  if (reached) {
    return "rounded-full px-2.5 py-1 text-xs font-medium text-indigo-600 hover:bg-indigo-50";
  }
  return "rounded-full px-2.5 py-1 text-xs font-medium text-slate-400";
}

export function Stepper({
  current,
  jobDescriptionId = null,
}: {
  current: StepKey;
  jobDescriptionId?: string | null;
}) {
  return (
    <nav aria-label="Create flow" className="mb-8">
      <ol className="flex flex-wrap items-center gap-1">
        {STEPS.map((step, index) => {
          const active = step.key === current;
          const href = hrefFor(step.key, jobDescriptionId);
          const reached = href !== null;
          const label = (
            <span className={stepClass(active, reached)}>{step.label}</span>
          );
          return (
            <li key={step.key} className="flex items-center gap-1">
              {index > 0 && <span className="text-slate-300">›</span>}
              {active || href === null ? (
                label
              ) : (
                <Link to={href}>{label}</Link>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}