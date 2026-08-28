import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  fetchGenerated,
  generateDocument,
  generatedLatexUrl,
  generatedPdfUrl,
  type GeneratedResume,
} from "../api/generation";
import { ResultPage } from "./ResultPage";

vi.mock("../api/generation", () => ({
  fetchGenerated: vi.fn(),
  generateDocument: vi.fn(),
  generatedPdfUrl: vi.fn(),
  generatedLatexUrl: vi.fn(),
}));

function generated(): GeneratedResume {
  return {
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
      warnings: ["No evidence found for 1 important requirements: Kubernetes."],
      unsupported_requirements: ["Excellent communication skills"],
    },
  };
}

function renderPage(url = "/create/result?jd=jd-1") {
  return render(
    <MemoryRouter initialEntries={[url]}>
      <ResultPage />
    </MemoryRouter>,
  );
}

describe("ResultPage", () => {
  afterEach(() => cleanup());

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(fetchGenerated).mockResolvedValue(generated());
    vi.mocked(generateDocument).mockResolvedValue(generated());
    vi.mocked(generatedPdfUrl).mockResolvedValue("blob:pdf");
    vi.mocked(generatedLatexUrl).mockResolvedValue("blob:tex");
  });

  it("renders the measured ATS analysis, never a fake score", async () => {
    renderPage();

    expect(await screen.findByText("ATS Compatibility Analysis")).toBeInTheDocument();
    expect(screen.getByText(/measured checks, not a score/)).toBeInTheDocument();
    expect(screen.getByText("100%")).toBeInTheDocument();
    expect(screen.getByText("N/A")).toBeInTheDocument();
    expect(screen.getByText("50%")).toBeInTheDocument();
    expect(screen.queryByText(/ATS score/i)).not.toBeInTheDocument();
  });

  it("reports the page count honestly and the machine-readability checks", async () => {
    renderPage();

    expect(await screen.findByText("Page count")).toBeInTheDocument();
    expect(screen.getByText("PDF text extraction")).toBeInTheDocument();
    expect(screen.getByText("Single column layout")).toBeInTheDocument();
    expect(screen.getByText("Standard section headings")).toBeInTheDocument();
    expect(screen.getByText("Name & contact in body")).toBeInTheDocument();
  });

  it("lists unsupported requirements and warnings explicitly", async () => {
    renderPage();

    expect(await screen.findByText("Unsupported requirements")).toBeInTheDocument();
    expect(screen.getByText("Excellent communication skills")).toBeInTheDocument();
    expect(screen.getByText("Warnings")).toBeInTheDocument();
    expect(screen.getByText(/No evidence found for 1 important requirements/)).toBeInTheDocument();
  });

  it("auto-generates the document when none exists yet", async () => {
    vi.mocked(fetchGenerated)
      .mockRejectedValueOnce(new Error("generated resume not found"))
      .mockResolvedValue(generated());

    renderPage();

    expect(await screen.findByTitle("Generated PDF")).toBeInTheDocument();
    expect(generateDocument).toHaveBeenCalledWith("jd-1");
  });

  it("previews the PDF and offers PDF + LaTeX downloads", async () => {
    renderPage();

    const pdf = await screen.findByTitle("Generated PDF");
    expect(pdf).toHaveAttribute("src", "blob:pdf");
    expect(screen.getByRole("link", { name: "Download PDF" })).toHaveAttribute(
      "href",
      "blob:pdf",
    );
    expect(screen.getByRole("link", { name: "Download LaTeX" })).toHaveAttribute(
      "href",
      "blob:tex",
    );
  });

  it("shows the structured error when generation fails", async () => {
    vi.mocked(fetchGenerated).mockRejectedValue(new Error("generated resume not found"));
    vi.mocked(generateDocument).mockRejectedValue(new Error("PDF could not be extracted"));

    renderPage();

    expect(await screen.findByText("PDF could not be extracted")).toBeInTheDocument();
  });

  it("warns when no job description id is provided", async () => {
    renderPage("/create/result");

    expect(
      await screen.findByText(/No job description id provided \(\?jd=\.\.\.\)\./),
    ).toBeInTheDocument();
  });
});