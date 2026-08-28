import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  fetchJob,
  fetchJobAnalysis,
  fetchJobDescription,
  listJobs,
  submitJobDescription,
  type JobAnalysis,
} from "../api/jobs";
import { JobAnalysisPage } from "./JobAnalysisPage";

vi.mock("../api/jobs", () => ({
  fetchJob: vi.fn(),
  fetchJobAnalysis: vi.fn(),
  fetchJobDescription: vi.fn(),
  listJobs: vi.fn(),
  submitJobDescription: vi.fn(),
}));

function analysis(): JobAnalysis {
  return {
    job_description_id: "jd-1",
    role: "Senior Backend Engineer",
    seniority: "Senior",
    requirements: [
      {
        requirement: "Experience with FastAPI",
        category: "REQUIRED",
        importance: "MEDIUM",
        context: "Experience with FastAPI",
      },
    ],
  };
}

function renderPage(url = "/create/job-analysis") {
  return render(
    <MemoryRouter initialEntries={[url]}>
      <JobAnalysisPage />
    </MemoryRouter>,
  );
}

describe("JobAnalysisPage", () => {
  afterEach(() => cleanup());

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(fetchJobAnalysis).mockRejectedValue(new Error("job analysis not found"));
    vi.mocked(fetchJobDescription).mockResolvedValue({
      id: "jd-1",
      company: "Acme",
      role: "Engineer",
      location: "Remote",
      jd_text: "Role: Engineer\n- Must have Python\n",
      created_at: "2026-08-28T12:00:00Z",
    });
    vi.mocked(listJobs).mockResolvedValue([]);
  });

  it("submits a job description and shows the analysis when the job completes", async () => {
    const user = userEvent.setup();
    vi.mocked(submitJobDescription).mockResolvedValue({
      job_description_id: "jd-1",
      job_id: "job-1",
      status: "PENDING",
    });
    vi.mocked(fetchJob).mockResolvedValue({
      id: "job-1",
      type: "ANALYZE",
      status: "SUCCEEDED",
      result: null,
      error: null,
    });
    vi.mocked(fetchJobAnalysis).mockResolvedValue(analysis());

    renderPage();

    await user.type(screen.getByPlaceholderText(/Paste the full job description here/), "Role: Engineer\n- Python");
    await user.click(screen.getByRole("button", { name: "Analyze" }));

    expect(await screen.findByText("Senior Backend Engineer")).toBeInTheDocument();
    expect(submitJobDescription).toHaveBeenCalledWith({
      company: "",
      role: "",
      location: "",
      jd_text: "Role: Engineer\n- Python",
    });
    expect(fetchJob).toHaveBeenCalledWith("job-1", expect.anything());
  });

  it("restores an analyzed session on back-navigation without re-running", async () => {
    vi.mocked(fetchJobAnalysis).mockResolvedValue(analysis());

    renderPage("/create/job-analysis?jd=jd-1");

    expect(await screen.findByText("Senior Backend Engineer")).toBeInTheDocument();
    expect(screen.getByText("Experience with FastAPI")).toBeInTheDocument();
    expect(fetchJobDescription).toHaveBeenCalledWith("jd-1");
    expect(fetchJobAnalysis).toHaveBeenCalledWith("jd-1");
    expect(submitJobDescription).not.toHaveBeenCalled();
  });

  it("prefills the job form from the stored Job Description when nothing is analyzed", async () => {
    renderPage("/create/job-analysis?jd=jd-1");

    expect(
      await screen.findByPlaceholderText(/Paste the full job description here/),
    ).toHaveValue("Role: Engineer\n- Must have Python\n");
    expect(screen.getByLabelText("Company")).toHaveValue("Acme");
    expect(screen.getByLabelText("Role")).toHaveValue("Engineer");
    expect(screen.getByLabelText("Location")).toHaveValue("Remote");
    expect(submitJobDescription).not.toHaveBeenCalled();
  });

  it("resumes an in-flight ANALYZE job on back-navigation", async () => {
    vi.mocked(fetchJobAnalysis)
      .mockRejectedValueOnce(new Error("job analysis not found"))
      .mockResolvedValue(analysis());
    vi.mocked(listJobs).mockResolvedValue([
      { id: "job-7", type: "ANALYZE", status: "RUNNING", result: null, error: null },
    ]);
    vi.mocked(fetchJob).mockResolvedValue({
      id: "job-7",
      type: "ANALYZE",
      status: "SUCCEEDED",
      result: null,
      error: null,
    });

    renderPage("/create/job-analysis?jd=jd-1");

    expect(await screen.findByText("Senior Backend Engineer")).toBeInTheDocument();
    expect(listJobs).toHaveBeenCalledWith("ANALYZE", "jd-1");
    expect(fetchJob).toHaveBeenCalledWith("job-7", expect.anything());
    expect(submitJobDescription).not.toHaveBeenCalled();
  });

  it("reports a failed ANALYZE job on back-navigation without resubmitting", async () => {
    vi.mocked(listJobs).mockResolvedValue([
      { id: "job-7", type: "ANALYZE", status: "FAILED", result: null, error: { code: "LLM_VALIDATION_FAILED", message: "bad output" } },
    ]);

    renderPage("/create/job-analysis?jd=jd-1");

    expect(await screen.findByText("bad output")).toBeInTheDocument();
    expect(submitJobDescription).not.toHaveBeenCalled();
  });

  it("shows the structured error when the session cannot be restored", async () => {
    vi.mocked(fetchJobDescription).mockRejectedValue(new Error("job description not found"));

    renderPage("/create/job-analysis?jd=jd-1");

    expect(await screen.findByText("job description not found")).toBeInTheDocument();
  });

  it("shows the stepper and highlights the analysis step", async () => {
    vi.mocked(fetchJobAnalysis).mockResolvedValue(analysis());

    renderPage("/create/job-analysis?jd=jd-1");

    expect(await screen.findByRole("navigation", { name: "Create flow" })).toBeInTheDocument();
    expect(screen.getByText("Analysis")).toBeInTheDocument();
  });
});