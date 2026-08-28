import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchDashboard, type ApplicationSummary, type DashboardSummary } from "../api/dashboard";

type LoadState =
  | { phase: "loading" }
  | { phase: "ready"; dashboard: DashboardSummary }
  | { phase: "error"; message: string };

function applicationLabel(application: ApplicationSummary): string {
  const parts = [application.company, application.role, application.location].filter(
    (part): part is string => Boolean(part),
  );
  return parts.length > 0 ? parts.join(" · ") : "Untitled application";
}

function ApplicationCard({ application }: { application: ApplicationSummary }) {
  const reopened = application.has_generated;
  return (
    <li className="flex items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm">
      <div className="min-w-0">
        <p className="truncate text-sm font-medium text-slate-900">
          {applicationLabel(application)}
        </p>
        <p className="mt-0.5 text-xs text-slate-500">
          {new Date(application.created_at).toLocaleDateString()}
        </p>
      </div>
      <Link
        to={
          reopened
            ? `/create/result?jd=${application.job_description_id}`
            : `/create/job-analysis?jd=${application.job_description_id}`
        }
        className="shrink-0 rounded-md bg-white px-3 py-1.5 text-xs font-medium text-indigo-600 ring-1 ring-inset ring-indigo-200 hover:bg-indigo-50"
      >
        {reopened ? "Reopen CV" : "Continue"}
      </Link>
    </li>
  );
}

export function DashboardPage() {
  const [state, setState] = useState<LoadState>({ phase: "loading" });

  useEffect(() => {
    const controller = new AbortController();
    fetchDashboard(controller.signal)
      .then((dashboard) => setState({ phase: "ready", dashboard }))
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
      <div className="mx-auto max-w-4xl px-4 py-10">
        <header className="flex items-center justify-between gap-3">
          <div>
            <h1 className="text-xl font-semibold text-slate-900">Dashboard</h1>
            <p className="mt-1 text-sm text-slate-500">
              One Master Resume in, tailored, ATS-safe CVs out.
            </p>
          </div>
          <Link
            to="/create"
            className="shrink-0 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-700"
          >
            Create Tailored CV
          </Link>
        </header>

        {state.phase === "loading" && <p className="mt-6 text-sm text-slate-500">Loading dashboard…</p>}

        {state.phase === "error" && <p className="mt-6 text-sm text-red-600">{state.message}</p>}

        {state.phase === "ready" && (
          <div className="mt-6 space-y-6">
            <section className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Tailored CVs
                </h2>
                <p className="mt-2 text-3xl font-semibold text-slate-900">
                  {state.dashboard.tailored_cv_count}
                </p>
              </div>
              <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Analyzed jobs
                </h2>
                <p className="mt-2 text-3xl font-semibold text-slate-900">
                  {state.dashboard.analyzed_jobs_count}
                </p>
              </div>
              <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Applications
                </h2>
                <p className="mt-2 text-3xl font-semibold text-slate-900">
                  {state.dashboard.recent_applications.length}
                </p>
              </div>
            </section>

            <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h2 className="text-lg font-semibold text-slate-900">Master CV</h2>
                  {state.dashboard.master_resume ? (
                    <p className="mt-1 text-sm text-slate-500">
                      {state.dashboard.master_resume.personal_information.full_name}
                      {state.dashboard.master_resume.personal_information.headline
                        ? ` — ${state.dashboard.master_resume.personal_information.headline}`
                        : ""}
                    </p>
                  ) : (
                    <p className="mt-1 text-sm text-slate-500">
                      No Master Resume yet. Create one to start tailoring.
                    </p>
                  )}
                </div>
                <Link
                  to="/resume"
                  className="shrink-0 rounded-md bg-white px-3 py-1.5 text-sm font-medium text-slate-700 ring-1 ring-inset ring-slate-300 hover:bg-slate-50"
                >
                  {state.dashboard.master_resume ? "Edit master" : "Create master"}
                </Link>
              </div>
            </section>

            <section>
              <div className="flex items-center justify-between">
                <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
                  Recent applications
                </h2>
                <Link to="/history" className="text-sm font-medium text-indigo-600 hover:text-indigo-700">
                  View history →
                </Link>
              </div>
              {state.dashboard.recent_applications.length === 0 ? (
                <p className="mt-3 text-sm text-slate-500">
                  No applications yet. Start with a Job Description.
                </p>
              ) : (
                <ul className="mt-3 space-y-2">
                  {state.dashboard.recent_applications.slice(0, 5).map((application) => (
                    <ApplicationCard key={application.job_description_id} application={application} />
                  ))}
                </ul>
              )}
            </section>
          </div>
        )}
      </div>
    </main>
  );
}