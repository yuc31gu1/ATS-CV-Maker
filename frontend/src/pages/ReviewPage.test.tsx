import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fetchJob } from "../api/jobs";
import { listResumes } from "../api/resume";
import {
  fetchTailored,
  submitRegenerate,
  submitReviewDecisions,
  submitTailor,
  type TailoredResume,
} from "../api/tailor";
import { ReviewPage } from "./ReviewPage";

vi.mock("../api/tailor", () => ({
  fetchTailored: vi.fn(),
  submitTailor: vi.fn(),
  submitReviewDecisions: vi.fn(),
  submitRegenerate: vi.fn(),
}));

vi.mock("../api/resume", () => ({
  listResumes: vi.fn(),
}));

vi.mock("../api/jobs", () => ({
  fetchJob: vi.fn(),
}));

function tailoredResume(): TailoredResume {
  return {
    job_description_id: "jd-1",
    resume_version_id: "version-1",
    resume_id: "resume-1",
    personal_information: { full_name: "Ada Lovelace", headline: "", email: "", phone: "", location: "", website: "" },
    summary: "Backend engineer who builds API platforms.",
    skills: { frameworks: ["FastAPI"] },
    experience: [],
    education: [],
    projects: [],
    certifications: [],
    created_at: "2026-08-28T12:00:00Z",
    changes: [
      {
        key: "summary",
        kind: "SUMMARY",
        section: "summary",
        original: "Backend engineer who builds API platforms.",
        tailored: "Backend engineer who builds API platforms.",
        reason: "Retained the summary to stay evidence-bound.",
        source_evidence_ids: ["experience:0:bullet:0"],
        status: "PENDING",
        edited_text: null,
      },
      {
        key: "experience:0:bullet:0",
        kind: "BULLET",
        section: "experience",
        original: "Built the ordering API with FastAPI",
        tailored: "Built the ordering API with FastAPI",
        reason: "Retained evidence-bound wording; aligned terminology with the Job Description.",
        source_evidence_ids: ["experience:0:bullet:0"],
        status: "PENDING",
        edited_text: null,
      },
    ],
  };
}

function renderPage(url = "/create/review?jd=jd-1") {
  return render(
    <MemoryRouter initialEntries={[url]}>
      <ReviewPage />
    </MemoryRouter>,
  );
}

describe("ReviewPage", () => {
  afterEach(() => cleanup());

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(fetchTailored).mockResolvedValue(tailoredResume());
    vi.mocked(listResumes).mockResolvedValue([
      { id: "resume-1", full_name: "Ada Lovelace" } as never,
    ]);
    vi.mocked(submitReviewDecisions).mockResolvedValue(tailoredResume());
    vi.mocked(submitRegenerate).mockResolvedValue({
      job_id: "job-2",
      job_description_id: "jd-1",
      resume_id: "resume-1",
      status: "PENDING",
    });
  });

  it("shows original / tailored / reason for each change", async () => {
    renderPage();

    expect((await screen.findAllByText("Built the ordering API with FastAPI")).length).toBe(2);
    expect(
      screen.getAllByText(/Backend engineer who builds API platforms\./).length,
    ).toBeGreaterThan(0);
    expect(screen.getAllByText(/Retained evidence-bound wording/).length).toBe(1);
    expect(screen.getAllByText(/Source evidence/).length).toBeGreaterThan(0);
    expect(screen.getAllByText("experience:0:bullet:0").length).toBeGreaterThan(0);
  });

  it("pins the review to a ResumeVersion, never the live master", async () => {
    renderPage();

    expect(await screen.findByText(/version-1/)).toBeInTheDocument();
    expect(screen.getByText(/never the live master/)).toBeInTheDocument();
  });

  it("auto-starts a TAILOR job and polls it when nothing is tailored yet", async () => {
    vi.mocked(fetchTailored)
      .mockRejectedValueOnce(new Error("tailored resume not found"))
      .mockResolvedValueOnce(tailoredResume());
    vi.mocked(submitTailor).mockResolvedValue({
      job_id: "job-1",
      job_description_id: "jd-1",
      resume_id: "resume-1",
      status: "PENDING",
    });
    vi.mocked(fetchJob).mockResolvedValue({
      id: "job-1",
      type: "TAILOR",
      status: "SUCCEEDED",
      result: null,
      error: null,
    });

    renderPage();

    expect((await screen.findAllByText("Built the ordering API with FastAPI")).length).toBe(2);
    expect(submitTailor).toHaveBeenCalledWith("resume-1", "jd-1");
    expect(fetchJob).toHaveBeenCalledWith("job-1", expect.anything());
  });

  it("accepts a change without mutating the master", async () => {
    const user = userEvent.setup();
    renderPage();

    const acceptButtons = await screen.findAllByRole("button", { name: "Accept" });
    await user.click(acceptButtons[0]);

    expect(submitReviewDecisions).toHaveBeenCalledWith("jd-1", [
      { key: "summary", action: "accept" },
    ]);
  });

  it("rejects a change", async () => {
    const user = userEvent.setup();
    renderPage();

    const rejectButtons = await screen.findAllByRole("button", { name: "Reject" });
    await user.click(rejectButtons[1]);

    expect(submitReviewDecisions).toHaveBeenCalledWith("jd-1", [
      { key: "experience:0:bullet:0", action: "reject" },
    ]);
  });

  it("edits a change inline", async () => {
    const user = userEvent.setup();
    vi.mocked(submitReviewDecisions).mockResolvedValue({
      ...tailoredResume(),
      summary: "Edited summary.",
      changes: [
        {
          ...tailoredResume().changes[0],
          status: "EDITED",
          edited_text: "Edited summary.",
        },
        tailoredResume().changes[1],
      ],
    });
    renderPage();

    const editButtons = await screen.findAllByRole("button", { name: "Edit" });
    await user.click(editButtons[0]);
    const textarea = screen.getByRole("textbox");
    await user.clear(textarea);
    await user.type(textarea, "Edited summary.");
    await user.click(screen.getByRole("button", { name: "Save edit" }));

    expect(submitReviewDecisions).toHaveBeenCalledWith("jd-1", [
      { key: "summary", action: "edit", text: "Edited summary." },
    ]);
  });

  it("regenerates a change through a TAILOR job", async () => {
    const user = userEvent.setup();
    vi.mocked(fetchJob).mockResolvedValue({
      id: "job-2",
      type: "TAILOR",
      status: "SUCCEEDED",
      result: null,
      error: null,
    });
    renderPage();

    const regenerateButtons = await screen.findAllByRole("button", { name: "Regenerate" });
    await user.click(regenerateButtons[1]);

    expect(submitRegenerate).toHaveBeenCalledWith("jd-1", "experience:0:bullet:0");
    expect((await screen.findAllByText("Built the ordering API with FastAPI")).length).toBe(2);
  });

  it("warns when no master resume exists", async () => {
    vi.mocked(fetchTailored).mockRejectedValue(new Error("tailored resume not found"));
    vi.mocked(listResumes).mockResolvedValue([]);

    renderPage();

    expect(
      await screen.findByText(/No master resume found\. Create one on the \/resume page first\./),
    ).toBeInTheDocument();
  });

  it("shows the structured error message when tailoring fails", async () => {
    vi.mocked(fetchTailored).mockRejectedValue(new Error("tailored resume not found"));
    vi.mocked(submitTailor).mockRejectedValue(new Error("match result not found"));

    renderPage();

    expect(await screen.findByText("match result not found")).toBeInTheDocument();
  });
});