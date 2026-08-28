import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  fetchAnalysis,
  fetchGenerated,
  generateDocument,
  generatedLatexUrl,
  generatedPdfUrl,
  type AtsAnalysis,
  type GeneratedResume,
} from "./generation";

const generated: GeneratedResume = {
  job_description_id: "jd-1",
  resume_version_id: "version-1",
  resume_id: "resume-1",
  latex_key: "latex/jd-1.tex",
  pdf_key: "pdf/jd-1.pdf",
  created_at: "2026-08-28T12:00:00Z",
  ats_analysis: {
    required_keyword_coverage: 1,
    preferred_keyword_coverage: null,
    evidence_coverage: 0.5,
    pdf_text_extraction: true,
    single_column: true,
    standard_headings: true,
    critical_info_in_body: true,
    unexpected_tables: 0,
    unexpected_graphics: 0,
    page_count: 1,
    warnings: [],
    unsupported_requirements: ["Excellent communication skills"],
  },
};

describe("generation API", () => {
  const originalFetch = globalThis.fetch;
  const originalCreateObjectURL = URL.createObjectURL;

  beforeEach(() => {
    globalThis.fetch = vi.fn();
    URL.createObjectURL = vi.fn(() => "blob:fake");
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    URL.createObjectURL = originalCreateObjectURL;
  });

  it("fetches the generated bundle metadata", async () => {
    vi.mocked(globalThis.fetch).mockResolvedValue(
      new Response(JSON.stringify(generated), { status: 200 }),
    );

    await expect(fetchGenerated("jd-1")).resolves.toEqual(generated);
    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/job-descriptions/jd-1/generated"),
      expect.anything(),
    );
  });

  it("kicks off synchronous document generation", async () => {
    vi.mocked(globalThis.fetch).mockResolvedValue(
      new Response(JSON.stringify(generated), { status: 201 }),
    );

    await expect(generateDocument("jd-1")).resolves.toEqual(generated);
    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/job-descriptions/jd-1/generated"),
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("fetches the measured ATS analysis", async () => {
    const analysis: AtsAnalysis = generated.ats_analysis!;
    vi.mocked(globalThis.fetch).mockResolvedValue(
      new Response(JSON.stringify(analysis), { status: 200 }),
    );

    await expect(fetchAnalysis("jd-1")).resolves.toEqual(analysis);
    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/job-descriptions/jd-1/generated/analysis"),
      expect.anything(),
    );
  });

  it("builds a blob URL for the PDF and LaTeX downloads", async () => {
    vi.mocked(globalThis.fetch).mockImplementation(async () => {
      return new Response(new Blob(["%PDF-1.4"]), { status: 200 });
    });

    await expect(generatedPdfUrl("jd-1")).resolves.toBe("blob:fake");
    await expect(generatedLatexUrl("jd-1")).resolves.toBe("blob:fake");
    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/generated/pdf"),
      expect.anything(),
    );
    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/generated/latex"),
      expect.anything(),
    );
  });

  it("throws the structured error message on failure", async () => {
    vi.mocked(globalThis.fetch).mockResolvedValue(
      new Response(
        JSON.stringify({
          error: { code: "PDF_VALIDATION_FAILED", message: "PDF could not be extracted" },
        }),
        { status: 502 },
      ),
    );

    await expect(generateDocument("jd-broken")).rejects.toThrow(
      "PDF could not be extracted",
    );
  });
});