import { useEffect, useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { fetchMatch, type EvidenceMatch, type MatchResult, type MatchStatus } from "../api/match";
import { listResumes } from "../api/resume";

type Phase =
  | { name: "form" }
  | { name: "loading" }
  | { name: "done"; result: MatchResult }
  | { name: "error"; message: string };

const STATUS_STYLES: Record<MatchStatus, string> = {
  STRONG_MATCH: "bg-green-50 text-green-700 border-green-200",
  PARTIAL_MATCH: "bg-amber-50 text-amber-700 border-amber-200",
  TRANSFERABLE: "bg-sky-50 text-sky-700 border-sky-200",
  NO_EVIDENCE: "bg-slate-100 text-slate-500 border-slate-200",
};

const STATUS_LABELS: Record<MatchStatus, string> = {
  STRONG_MATCH: "Strong match",
  PARTIAL_MATCH: "Partial match",
  TRANSFERABLE: "Transferable",
  NO_EVIDENCE: "No evidence",
};

function StatusBadge({ status }: { status: MatchStatus }) {
  return (
    <span
      className={`inline-flex rounded-full border px-2.5 py-0.5 text-xs font-medium ${STATUS_STYLES[status]}`}
    >
      {STATUS_LABELS[status]}
    </span>
  );
}

function EvidenceCell({ match }: { match: EvidenceMatch }) {
  if (match.evidence.length === 0) {
    return <span className="text-sm text-slate-400">—</span>;
  }
  return (
    <ul className="space-y-1">
      {match.evidence.map((text, index) => (
        <li key={index} className="text-sm text-slate-700">
          {text}
        </li>
      ))}
    </ul>
  );
}

const inputClass =
  "mt-1 block w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500";

export function MatchPage() {
  const [searchParams] = useSearchParams();
  const [phase, setPhase] = useState<Phase>({ name: "form" });
  const [jdId, setJdId] = useState(searchParams.get("jd") ?? "");

  async function load(jobDescriptionId: string) {
    setPhase({ name: "loading" });
    try {
      const resumes = await listResumes();
      if (resumes.length === 0) {
        setPhase({
          name: "error",
          message: "No master resume found. Create one on the /resume page first.",
        });
        return;
      }
      const resume = resumes[0];
      const result = await fetchMatch(jobDescriptionId, resume.id);
      setPhase({ name: "done", result });
    } catch (err) {
      setPhase({ name: "error", message: err instanceof Error ? err.message : String(err) });
    }
  }

  useEffect(() => {
    const jdFromUrl = searchParams.get("jd");
    if (jdFromUrl) {
      setJdId(jdFromUrl);
      void load(jdFromUrl);
    }
  }, []);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!jdId.trim()) {
      return;
    }
    void load(jdId.trim());
  }

  return (
    <main className="min-h-screen bg-slate-50">
      <div className="mx-auto max-w-4xl px-4 py-10">
        <h1 className="text-xl font-semibold text-slate-900">Candidate Evidence Matching</h1>
        <p className="mt-1 text-sm text-slate-500">
          Every job requirement is matched against evidence in your Master Resume. Statuses are
          assigned by deterministic rules over a curated Skill Catalog — never by the LLM
          (ADR-0002).
        </p>

        {phase.name === "form" && (
          <form onSubmit={handleSubmit} className="mt-6 max-w-md space-y-3">
            <label className="block text-sm text-slate-600">
              Job description id
              <input
                className={inputClass}
                value={jdId}
                onChange={(event) => setJdId(event.target.value)}
                placeholder="e.g. 3fa85f64-5717-4562-b3fc-2c963f66afa6"
              />
            </label>
            <button
              type="submit"
              disabled={!jdId.trim()}
              className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-700 disabled:cursor-not-allowed disabled:bg-slate-300"
            >
              Load matches
            </button>
          </form>
        )}

        {phase.name === "loading" && (
          <p className="mt-6 text-sm text-slate-500">Matching requirements against evidence…</p>
        )}

        {phase.name === "error" && <p className="mt-6 text-sm text-red-600">{phase.message}</p>}

        {phase.name === "done" && (
          <div className="mt-6 space-y-4">
            {phase.result.matches.map((match) => (
              <div
                key={`${match.category}:${match.requirement}`}
                className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"
              >
                <div className="flex flex-wrap items-start gap-2">
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-slate-900">{match.requirement}</p>
                    <div className="mt-1 flex flex-wrap items-center gap-2">
                      <span className="rounded-full bg-indigo-50 px-2 py-0.5 text-xs font-medium text-indigo-700">
                        {match.category}
                      </span>
                      <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">
                        {match.importance}
                      </span>
                      <StatusBadge status={match.status} />
                      {match.ambiguous && (
                        <span className="rounded-full border border-orange-200 bg-orange-50 px-2 py-0.5 text-xs font-medium text-orange-700">
                          Needs review
                        </span>
                      )}
                    </div>
                  </div>
                </div>
                <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
                  <div>
                    <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                      Evidence
                    </h3>
                    <div className="mt-1">
                      <EvidenceCell match={match} />
                    </div>
                  </div>
                  <div>
                    <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                      Why
                    </h3>
                    <p className="mt-1 text-sm text-slate-600">{match.rationale}</p>
                  </div>
                </div>
              </div>
            ))}
            <p className="text-xs text-slate-400">
              Ambiguous and transferable hits are surfaced for your review and are never presented
              as direct experience.
            </p>
            <Link
              to={`/create/review?jd=${phase.result.job_description_id}`}
              className="mt-4 inline-block rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-700"
            >
              Tailor & review →
            </Link>
          </div>
        )}
      </div>
    </main>
  );
}