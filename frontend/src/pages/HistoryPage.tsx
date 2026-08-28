import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchApplications, type ApplicationSummary } from "../api/dashboard";
import { applicationLabel } from "../domain/application";

type LoadState =
  | { phase: "loading" }
  | { phase: "ready"; applications: ApplicationSummary[] }
  | { phase: "error"; message: string };

function StageBadges({ application }: { application: ApplicationSummary }) {
  const badges: string[] = [];
  if (application.has_analysis) {
    badges.push("Analyzed");
  }
  if (application.has_tailored) {
    badges.push("Tailored");
  }
  if (application.has_generated) {
    badges.push("Generated");
  }
  if (badges.length === 0) {
    return <span className="text-xs text-slate-400">Not started</span>;
  }
  return (
    <div className="flex flex-wrap gap-1">
      {badges.map((badge) => (
        <span
          key={badge}
          className="rounded-full bg-indigo-50 px-2 py-0.5 text-xs font-medium text-indigo-700"
        >
          {badge}
        </span>
      ))}
    </div>
  );
}

export function HistoryPage() {
  const [state, setState] = useState<LoadState>({ phase: "loading" });

  useEffect(() => {
    const controller = new AbortController();
    fetchApplications(controller.signal)
      .then((applications) => setState({ phase: "ready", applications }))
      .catch((err: unknown) => {
        if (err instanceof Error && err.name === "AbortError") {
          return;
        }
        setState({
          phase: "error",
          message: err instanceof Error ? err.message : String(err),
        });
      });
    return () => controller.abort();
  }, []);

  return (
    <main className="min-h-screen bg-slate-50">
      <div className="mx-auto max-w-3xl px-4 py-10">
        <header className="flex items-center justify-between gap-3">
          <div>
            <h1 className="text-xl font-semibold text-slate-900">Application history</h1>
            <p className="mt-1 text-sm text-slate-500">
              Prior applications and generated resumes, each pinned to the ResumeVersion it was
              built from.
            </p>
          </div>
          <Link
            to="/dashboard"
            className="shrink-0 rounded-md bg-white px-3 py-1.5 text-sm font-medium text-slate-700 ring-1 ring-inset ring-slate-300 hover:bg-slate-50"
          >
            ← Dashboard
          </Link>
        </header>

        {state.phase === "loading" && <p className="mt-6 text-sm text-slate-500">Loading history…</p>}

        {state.phase === "error" && <p className="mt-6 text-sm text-red-600">{state.message}</p>}

        {state.phase === "ready" &&
          (state.applications.length === 0 ? (
            <p className="mt-6 text-sm text-slate-500">
              No applications yet. Start one from the dashboard.
            </p>
          ) : (
            <ul className="mt-6 space-y-2">
              {state.applications.map((application) => (
                <li
                  key={application.job_description_id}
                  className="flex items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm"
                >
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-slate-900">
                      {applicationLabel(application)}
                    </p>
                    <p className="mt-0.5 text-xs text-slate-500">
                      {new Date(application.created_at).toLocaleDateString()}
                    </p>
                    <div className="mt-1.5">
                      <StageBadges application={application} />
                    </div>
                  </div>
                  <Link
                    to={
                      application.has_generated
                        ? `/create/result?jd=${application.job_description_id}`
                        : `/create/job-analysis?jd=${application.job_description_id}`
                    }
                    className="shrink-0 rounded-md bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white shadow-sm hover:bg-indigo-700"
                  >
                    {application.has_generated ? "Reopen CV" : "Continue"}
                  </Link>
                </li>
              ))}
            </ul>
          ))}
      </div>
    </main>
  );
}