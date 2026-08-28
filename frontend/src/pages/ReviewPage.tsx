import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Stepper } from "../components/Stepper";
import { fetchJob } from "../api/jobs";
import { listResumes } from "../api/resume";
import {
  fetchTailored,
  submitRegenerate,
  submitReviewDecisions,
  submitTailor,
  type ReviewDecision,
  type TailoredChange,
  type TailoredResume,
} from "../api/tailor";

type Phase =
  | { name: "starting" }
  | { name: "tailoring"; jobId: string; jobDescriptionId: string }
  | { name: "regenerating"; jobId: string; jobDescriptionId: string }
  | { name: "done"; resume: TailoredResume }
  | { name: "error"; message: string };

const POLL_INTERVAL_MS = 800;

const STATUS_STYLES: Record<TailoredChange["status"], string> = {
  PENDING: "bg-slate-100 text-slate-600 border-slate-200",
  ACCEPTED: "bg-green-50 text-green-700 border-green-200",
  REJECTED: "bg-red-50 text-red-700 border-red-200",
  EDITED: "bg-indigo-50 text-indigo-700 border-indigo-200",
};

const STATUS_LABELS: Record<TailoredChange["status"], string> = {
  PENDING: "Pending",
  ACCEPTED: "Accepted",
  REJECTED: "Rejected",
  EDITED: "Edited",
};

function StatusBadge({ status }: { status: TailoredChange["status"] }) {
  return (
    <span
      className={`inline-flex rounded-full border px-2.5 py-0.5 text-xs font-medium ${STATUS_STYLES[status]}`}
    >
      {STATUS_LABELS[status]}
    </span>
  );
}

function ChangeCard({
  change,
  editing,
  onStartEdit,
  onCancelEdit,
  onSaveEdit,
  onAccept,
  onReject,
  onRegenerate,
  busy,
}: {
  change: TailoredChange;
  editing: boolean;
  onStartEdit: () => void;
  onCancelEdit: () => void;
  onSaveEdit: (text: string) => void;
  onAccept: () => void;
  onReject: () => void;
  onRegenerate: () => void;
  busy: boolean;
}) {
  const [draft, setDraft] = useState(change.tailored);
  useEffect(() => setDraft(change.tailored), [change.tailored]);

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="rounded-full bg-indigo-50 px-2 py-0.5 text-xs font-medium text-indigo-700">
            {change.kind === "SUMMARY" ? "Summary" : change.section}
          </span>
          <span className="font-mono text-xs text-slate-400">{change.key}</span>
          <StatusBadge status={change.status} />
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={onAccept}
            disabled={busy}
            className="rounded-md bg-green-600 px-3 py-1.5 text-xs font-medium text-white shadow-sm hover:bg-green-700 disabled:cursor-not-allowed disabled:bg-slate-300"
          >
            Accept
          </button>
          <button
            type="button"
            onClick={onReject}
            disabled={busy}
            className="rounded-md bg-white px-3 py-1.5 text-xs font-medium text-slate-700 ring-1 ring-inset ring-slate-300 hover:bg-slate-50 disabled:cursor-not-allowed disabled:text-slate-300"
          >
            Reject
          </button>
          {editing ? (
            <>
              <button
                type="button"
                onClick={() => onSaveEdit(draft)}
                disabled={busy || !draft.trim()}
                className="rounded-md bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white shadow-sm hover:bg-indigo-700 disabled:cursor-not-allowed disabled:bg-slate-300"
              >
                Save edit
              </button>
              <button
                type="button"
                onClick={onCancelEdit}
                disabled={busy}
                className="rounded-md bg-white px-3 py-1.5 text-xs font-medium text-slate-700 ring-1 ring-inset ring-slate-300 hover:bg-slate-50 disabled:cursor-not-allowed"
              >
                Cancel
              </button>
            </>
          ) : (
            <button
              type="button"
              onClick={onStartEdit}
              disabled={busy}
              className="rounded-md bg-white px-3 py-1.5 text-xs font-medium text-slate-700 ring-1 ring-inset ring-slate-300 hover:bg-slate-50 disabled:cursor-not-allowed disabled:text-slate-300"
            >
              Edit
            </button>
          )}
          <button
            type="button"
            onClick={onRegenerate}
            disabled={busy}
            className="rounded-md bg-amber-500 px-3 py-1.5 text-xs font-medium text-white shadow-sm hover:bg-amber-600 disabled:cursor-not-allowed disabled:bg-slate-300"
          >
            Regenerate
          </button>
        </div>
      </div>

      <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
        <div>
          <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Original
          </h3>
          <p className="mt-1 text-sm text-slate-600">{change.original}</p>
        </div>
        <div>
          <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Tailored
          </h3>
          {editing ? (
            <textarea
              className="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              rows={3}
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
            />
          ) : (
            <p className="mt-1 text-sm text-slate-900">{change.tailored}</p>
          )}
        </div>
      </div>

      <div className="mt-3">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          Why
        </h3>
        <p className="mt-1 text-sm text-slate-600">{change.reason}</p>
        {change.source_evidence_ids.length > 0 && (
          <p className="mt-2 text-xs text-slate-400">
            Source evidence:{" "}
            <span className="font-mono">{change.source_evidence_ids.join(", ")}</span>
          </p>
        )}
      </div>
    </div>
  );
}

export function ReviewPage() {
  const [searchParams] = useSearchParams();
  const [phase, setPhase] = useState<Phase>({ name: "starting" });
  const [editingKey, setEditingKey] = useState<string | null>(null);

  const jobDescriptionId = searchParams.get("jd") ?? "";
  const resume =
    phase.name === "done"
      ? phase.resume
      : null;

  async function start() {
    setPhase({ name: "starting" });
    if (!jobDescriptionId) {
      setPhase({ name: "error", message: "No job description id provided (?jd=...)." });
      return;
    }
    try {
      const existing = await fetchTailored(jobDescriptionId);
      setPhase({ name: "done", resume: existing });
      return;
    } catch {
      // not tailored yet — kick off a TAILOR job below
    }
    try {
      const resumes = await listResumes();
      if (resumes.length === 0) {
        setPhase({
          name: "error",
          message: "No master resume found. Create one on the /resume page first.",
        });
        return;
      }
      const submitted = await submitTailor(resumes[0].id!, jobDescriptionId);
      setPhase({
        name: "tailoring",
        jobId: submitted.job_id,
        jobDescriptionId,
      });
    } catch (err) {
      setPhase({ name: "error", message: err instanceof Error ? err.message : String(err) });
    }
  }

  useEffect(() => {
    void start();
  }, []);

  useEffect(() => {
    if (phase.name !== "tailoring" && phase.name !== "regenerating") {
      return;
    }
    const jobId = phase.jobId;
    const controller = new AbortController();
    let interval: number | undefined;

    async function tick() {
      try {
        const job = await fetchJob(jobId, controller.signal);
        if (job.status === "SUCCEEDED") {
          const next = await fetchTailored(jobDescriptionId, controller.signal);
          setPhase({ name: "done", resume: next });
          window.clearInterval(interval);
        } else if (job.status === "FAILED") {
          setPhase({ name: "error", message: job.error?.message ?? "Tailoring job failed" });
          window.clearInterval(interval);
        }
      } catch (err) {
        if (!controller.signal.aborted) {
          setPhase({ name: "error", message: err instanceof Error ? err.message : String(err) });
          window.clearInterval(interval);
        }
      }
    }

    void tick();
    interval = window.setInterval(() => void tick(), POLL_INTERVAL_MS);
    return () => {
      window.clearInterval(interval);
      controller.abort();
    };
  }, [phase]);

  async function runRegenerate(changeKey: string) {
    if (phase.name !== "done") {
      return;
    }
    try {
      const submitted = await submitRegenerate(jobDescriptionId, changeKey);
      setPhase({ name: "regenerating", jobId: submitted.job_id, jobDescriptionId });
    } catch (err) {
      setPhase({ name: "error", message: err instanceof Error ? err.message : String(err) });
    }
  }

  async function applyDecision(decision: ReviewDecision) {
    if (phase.name !== "done") {
      return;
    }
    try {
      const next = await submitReviewDecisions(jobDescriptionId, [decision]);
      setPhase({ name: "done", resume: next });
      setEditingKey(null);
    } catch (err) {
      setPhase({ name: "error", message: err instanceof Error ? err.message : String(err) });
    }
  }

  return (
    <main className="min-h-screen bg-slate-50">
      <div className="mx-auto max-w-4xl px-4 py-10">
        <Stepper current="review" jobDescriptionId={jobDescriptionId} />
        <div className="flex items-start justify-between gap-3">
          <div>
            <h1 className="text-xl font-semibold text-slate-900">Tailoring Review</h1>
            <p className="mt-1 text-sm text-slate-500">
              Every change shows the original, the tailored text, and why. You stay in
              control — accept, reject, regenerate, or edit each change. The Master
              Resume is never mutated.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Link
              to={`/create/match?jd=${jobDescriptionId}`}
              className="shrink-0 rounded-md bg-white px-3 py-1.5 text-sm font-medium text-slate-700 ring-1 ring-inset ring-slate-300 hover:bg-slate-50"
            >
              ← Back to matches
            </Link>
            <Link
              to={`/create/result?jd=${jobDescriptionId}`}
              className="shrink-0 rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white shadow-sm hover:bg-indigo-700"
            >
              Generate & analyze →
            </Link>
          </div>
        </div>

        {phase.name === "starting" && (
          <p className="mt-6 text-sm text-slate-500">Loading tailoring review…</p>
        )}

        {phase.name === "tailoring" && (
          <div className="mt-6 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex items-center gap-3">
              <span className="h-2 w-2 animate-pulse rounded-full bg-indigo-500" />
              <p className="text-sm text-slate-600">
                Tailoring your resume to this job… this can take a moment.
              </p>
            </div>
          </div>
        )}

        {phase.name === "regenerating" && (
          <div className="mt-6 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex items-center gap-3">
              <span className="h-2 w-2 animate-pulse rounded-full bg-amber-500" />
              <p className="text-sm text-slate-600">
                Regenerating the change… this can take a moment.
              </p>
            </div>
          </div>
        )}

        {phase.name === "error" && <p className="mt-6 text-sm text-red-600">{phase.message}</p>}

        {phase.name === "done" && (
          <div className="mt-6 space-y-4">
            <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
              <p className="text-sm font-medium text-slate-900">{resume?.summary}</p>
              <p className="mt-2 text-xs text-slate-400">
                Pinned to ResumeVersion <span className="font-mono">{resume?.resume_version_id}</span>
                — never the live master.
              </p>
            </div>
            {resume?.changes.map((change) => (
              <ChangeCard
                key={change.key}
                change={change}
                editing={editingKey === change.key}
                onStartEdit={() => setEditingKey(change.key)}
                onCancelEdit={() => setEditingKey(null)}
                onSaveEdit={(text) => void applyDecision({ key: change.key, action: "edit", text })}
                onAccept={() => void applyDecision({ key: change.key, action: "accept" })}
                onReject={() => void applyDecision({ key: change.key, action: "reject" })}
                onRegenerate={() => void runRegenerate(change.key)}
                busy={false}
              />
            ))}
          </div>
        )}
      </div>
    </main>
  );
}