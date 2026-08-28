import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
  fetchGenerated,
  generateDocument,
  generatedLatexUrl,
  generatedPdfUrl,
  type AtsAnalysis,
  type GeneratedResume,
} from "../api/generation";

type Phase =
  | { name: "starting" }
  | { name: "generating" }
  | { name: "done"; generated: GeneratedResume; pdfUrl: string; latexUrl: string }
  | { name: "error"; message: string };

function CoverageRow({ label, value }: { label: string; value: number | null }) {
  const percent = value === null ? null : Math.round(value * 100);
  return (
    <div>
      <div className="flex items-center justify-between text-sm">
        <span className="font-medium text-slate-700">{label}</span>
        <span className="font-semibold text-slate-900">
          {percent === null ? "N/A" : `${percent}%`}
        </span>
      </div>
      <div className="mt-1 h-2 w-full overflow-hidden rounded-full bg-slate-100">
        <div
          className="h-full rounded-full bg-indigo-500"
          style={{ width: percent === null ? "0%" : `${percent}%` }}
        />
      </div>
    </div>
  );
}

function CheckRow({ label, ok }: { label: string; ok: boolean }) {
  return (
    <li className="flex items-center gap-2 text-sm">
      <span
        className={`inline-flex h-5 w-5 items-center justify-center rounded-full text-xs font-bold ${
          ok ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"
        }`}
      >
        {ok ? "✓" : "✗"}
      </span>
      <span className="text-slate-700">{label}</span>
    </li>
  );
}

function AnalysisPanel({ analysis }: { analysis: AtsAnalysis }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <h2 className="text-lg font-semibold text-slate-900">ATS Compatibility Analysis</h2>
      <p className="mt-1 text-sm text-slate-500">
        These are measured checks, not a score — there is no single "ATS rating". Page count is
        reported honestly and is never auto-fitted.
      </p>

      <div className="mt-5 space-y-4">
        <CoverageRow
          label="Required keyword coverage"
          value={analysis.required_keyword_coverage}
        />
        <CoverageRow
          label="Preferred keyword coverage"
          value={analysis.preferred_keyword_coverage}
        />
        <CoverageRow label="Evidence coverage" value={analysis.evidence_coverage} />
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 sm:grid-cols-2">
        <div>
          <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            PDF machine-readability
          </h3>
          <ul className="mt-2 space-y-2">
            <CheckRow label="PDF text extraction" ok={analysis.pdf_text_extraction} />
            <CheckRow label="Single column layout" ok={analysis.single_column} />
            <CheckRow label="Standard section headings" ok={analysis.standard_headings} />
            <CheckRow label="Name & contact in body" ok={analysis.critical_info_in_body} />
          </ul>
        </div>
        <div className="space-y-3">
          <div className="flex items-center justify-between text-sm">
            <span className="font-medium text-slate-700">Unexpected tables</span>
            <span className="text-slate-900">{analysis.unexpected_tables}</span>
          </div>
          <div className="flex items-center justify-between text-sm">
            <span className="font-medium text-slate-700">Unexpected graphics</span>
            <span className="text-slate-900">{analysis.unexpected_graphics}</span>
          </div>
          <div className="flex items-center justify-between text-sm">
            <span className="font-medium text-slate-700">Page count</span>
            <span className="text-slate-900">{analysis.page_count}</span>
          </div>
        </div>
      </div>

      {analysis.unsupported_requirements.length > 0 && (
        <div className="mt-6">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Unsupported requirements
          </h3>
          <p className="mt-1 text-sm text-slate-500">
            These could not be measured against the Skill Catalog and are listed explicitly:
          </p>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-700">
            {analysis.unsupported_requirements.map((requirement) => (
              <li key={requirement}>{requirement}</li>
            ))}
          </ul>
        </div>
      )}

      {analysis.warnings.length > 0 && (
        <div className="mt-6">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Warnings
          </h3>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-amber-700">
            {analysis.warnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

export function ResultPage() {
  const [searchParams] = useSearchParams();
  const [phase, setPhase] = useState<Phase>({ name: "starting" });

  const jobDescriptionId = searchParams.get("jd") ?? "";

  async function load() {
    setPhase({ name: "starting" });
    if (!jobDescriptionId) {
      setPhase({ name: "error", message: "No job description id provided (?jd=...)." });
      return;
    }
    setPhase({ name: "generating" });
    try {
      let generated: GeneratedResume;
      try {
        generated = await fetchGenerated(jobDescriptionId);
      } catch {
        generated = await generateDocument(jobDescriptionId);
      }
      const [pdfUrl, latexUrl] = await Promise.all([
        generatedPdfUrl(jobDescriptionId),
        generatedLatexUrl(jobDescriptionId),
      ]);
      setPhase({ name: "done", generated, pdfUrl, latexUrl });
    } catch (err) {
      setPhase({ name: "error", message: err instanceof Error ? err.message : String(err) });
    }
  }

  useEffect(() => {
    void load();
  }, []);

  return (
    <main className="min-h-screen bg-slate-50">
      <div className="mx-auto max-w-5xl px-4 py-10">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h1 className="text-xl font-semibold text-slate-900">Generated PDF & ATS Analysis</h1>
            <p className="mt-1 text-sm text-slate-500">
              Your validated PDF is previewed below. What you review is what you download.
            </p>
          </div>
          <Link
            to={`/create/review?jd=${jobDescriptionId}`}
            className="shrink-0 rounded-md bg-white px-3 py-1.5 text-sm font-medium text-slate-700 ring-1 ring-inset ring-slate-300 hover:bg-slate-50"
          >
            ← Back to review
          </Link>
        </div>

        {phase.name === "starting" && (
          <p className="mt-6 text-sm text-slate-500">Loading generated document…</p>
        )}

        {phase.name === "generating" && (
          <div className="mt-6 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex items-center gap-3">
              <span className="h-2 w-2 animate-pulse rounded-full bg-indigo-500" />
              <p className="text-sm text-slate-600">
                Compiling, validating, and analyzing your PDF… this can take a moment.
              </p>
            </div>
          </div>
        )}

        {phase.name === "error" && <p className="mt-6 text-sm text-red-600">{phase.message}</p>}

        {phase.name === "done" && (
          <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
            <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
              <div className="flex items-center justify-between gap-2">
                <h2 className="text-sm font-semibold text-slate-900">PDF preview</h2>
                <div className="flex items-center gap-2">
                  <a
                    href={phase.pdfUrl}
                    download={`resume-${jobDescriptionId}.pdf`}
                    className="rounded-md bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white shadow-sm hover:bg-indigo-700"
                  >
                    Download PDF
                  </a>
                  <a
                    href={phase.latexUrl}
                    download={`resume-${jobDescriptionId}.tex`}
                    className="rounded-md bg-white px-3 py-1.5 text-xs font-medium text-slate-700 ring-1 ring-inset ring-slate-300 hover:bg-slate-50"
                  >
                    Download LaTeX
                  </a>
                </div>
              </div>
              <iframe
                title="Generated PDF"
                src={phase.pdfUrl}
                className="mt-3 h-[72vh] w-full rounded-md border border-slate-200 bg-slate-100"
              />
            </div>

            {phase.generated.ats_analysis && (
              <AnalysisPanel analysis={phase.generated.ats_analysis} />
            )}
          </div>
        )}
      </div>
    </main>
  );
}