import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fetchMatch } from "../api/match";
import { listResumes } from "../api/resume";
import type { MatchResult } from "../api/match";
import { MatchPage } from "./MatchPage";

vi.mock("../api/match", () => ({
  fetchMatch: vi.fn(),
}));

vi.mock("../api/resume", () => ({
  listResumes: vi.fn(),
}));

function matchResult(): MatchResult {
  return {
    job_description_id: "jd-1",
    resume_id: "resume-1",
    created_at: "2026-08-28T12:00:00Z",
    matches: [
      {
        requirement: "Experience with FastAPI",
        category: "REQUIRED",
        importance: "MEDIUM",
        status: "STRONG_MATCH",
        matched_skill: "fastapi",
        ambiguous: false,
        rationale: "Skill 'fastapi' is listed and substantiated by experience or projects.",
        evidence_ids: ["experience:0:bullet:0"],
        evidence: ["Built the ordering API with FastAPI"],
      },
      {
        requirement: "Experience with Django preferred",
        category: "PREFERRED",
        importance: "LOW",
        status: "TRANSFERABLE",
        matched_skill: "fastapi",
        ambiguous: true,
        rationale:
          "No direct evidence for the required skill; adjacent skill 'fastapi' is present.",
        evidence_ids: [],
        evidence: [],
      },
      {
        requirement: "Experience with Kafka",
        category: "REQUIRED",
        importance: "HIGH",
        status: "NO_EVIDENCE",
        matched_skill: "kafka",
        ambiguous: false,
        rationale: "No evidence found for skill 'kafka'.",
        evidence_ids: [],
        evidence: [],
      },
    ],
  };
}

function renderPage(url = "/create/match?jd=jd-1") {
  return render(
    <MemoryRouter initialEntries={[url]}>
      <MatchPage />
    </MemoryRouter>,
  );
}

describe("MatchPage", () => {
  afterEach(() => cleanup());

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(listResumes).mockResolvedValue([
      { id: "resume-1", full_name: "Ada Lovelace" } as never,
    ]);
    vi.mocked(fetchMatch).mockResolvedValue(matchResult());
  });

  it("renders the requirement–evidence–match table from the jd in the URL", async () => {
    renderPage();

    expect(await screen.findByText("Experience with FastAPI")).toBeInTheDocument();
    expect(await screen.findByText("Strong match")).toBeInTheDocument();
    expect(screen.getByText("Built the ordering API with FastAPI")).toBeInTheDocument();
    expect(screen.getByText("Experience with Django preferred")).toBeInTheDocument();
    expect(screen.getByText("Transferable")).toBeInTheDocument();

    expect(fetchMatch).toHaveBeenCalledWith("jd-1", "resume-1");
    expect(listResumes).toHaveBeenCalled();
  });

  it("surfaces ambiguous matches for human review", async () => {
    renderPage();

    const needsReview = await screen.findByText("Needs review");
    expect(needsReview).toBeInTheDocument();
    expect(screen.getByText("No evidence")).toBeInTheDocument();
  });

  it("shows the deterministic-rules note and never claims direct experience", async () => {
    renderPage();

    expect(
      await screen.findByText(/assigned by deterministic rules over a curated Skill Catalog/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        /Ambiguous and transferable hits are surfaced for your review and are never presented as direct experience/i,
      ),
    ).toBeInTheDocument();
  });

  it("loads matches from the form when no jd is in the URL", async () => {
    const user = userEvent.setup();
    renderPage("/create/match");

    const input = screen.getByLabelText("Job description id");
    await user.type(input, "jd-42");
    await user.click(screen.getByRole("button", { name: "Load matches" }));

    expect(await screen.findByText("Experience with FastAPI")).toBeInTheDocument();
    expect(fetchMatch).toHaveBeenCalledWith("jd-42", "resume-1");
  });

  it("warns when no master resume exists", async () => {
    vi.mocked(listResumes).mockResolvedValue([]);

    renderPage();

    expect(
      await screen.findByText(/No master resume found\. Create one on the \/resume page first\./),
    ).toBeInTheDocument();
    expect(fetchMatch).not.toHaveBeenCalled();
  });

  it("shows the structured error message when matching fails", async () => {
    vi.mocked(fetchMatch).mockRejectedValue(new Error("job analysis not found"));

    renderPage();

    expect(await screen.findByText("job analysis not found")).toBeInTheDocument();
  });
});