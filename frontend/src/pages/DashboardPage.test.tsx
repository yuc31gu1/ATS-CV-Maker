import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fetchDashboard, type DashboardSummary } from "../api/dashboard";
import { DashboardPage } from "./DashboardPage";

vi.mock("../api/dashboard", () => ({
  fetchDashboard: vi.fn(),
}));

function dashboard(): DashboardSummary {
  return {
    master_resume: {
      id: "resume-1",
      schema_version: 1,
      personal_information: {
        full_name: "Ada Lovelace",
        headline: "Backend engineer",
        email: "ada@example.com",
        phone: "",
        location: "",
        website: "",
      },
      summary: "",
      skills: {},
      experience: [],
      education: [],
      projects: [],
      certifications: [],
    },
    tailored_cv_count: 4,
    analyzed_jobs_count: 7,
    recent_applications: [
      {
        job_description_id: "jd-1",
        company: "Acme",
        role: "Engineer",
        location: null,
        created_at: "2026-08-28T12:00:00Z",
        has_analysis: true,
        has_tailored: true,
        has_generated: true,
      },
      {
        job_description_id: "jd-2",
        company: null,
        role: null,
        location: null,
        created_at: "2026-08-27T12:00:00Z",
        has_analysis: false,
        has_tailored: false,
        has_generated: false,
      },
    ],
  };
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/dashboard"]}>
      <DashboardPage />
    </MemoryRouter>,
  );
}

describe("DashboardPage", () => {
  afterEach(() => cleanup());

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(fetchDashboard).mockResolvedValue(dashboard());
  });

  it("shows the counts, master CV, and the Create Tailored CV CTA", async () => {
    renderPage();

    expect(await screen.findByText("Tailored CVs")).toBeInTheDocument();
    expect(screen.getByText("4")).toBeInTheDocument();
    expect(screen.getByText("Analyzed jobs")).toBeInTheDocument();
    expect(screen.getByText("7")).toBeInTheDocument();
    expect(screen.getByText(/Ada Lovelace/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Create Tailored CV" })).toHaveAttribute(
      "href",
      "/create",
    );
    expect(screen.getByRole("link", { name: "Edit master" })).toHaveAttribute("href", "/resume");
  });

  it("lists recent applications and reopens a generated CV", async () => {
    renderPage();

    expect(await screen.findByText("Recent applications")).toBeInTheDocument();
    expect(screen.getByText(/Acme · Engineer/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Reopen CV" })).toHaveAttribute(
      "href",
      "/create/result?jd=jd-1",
    );
    expect(screen.getByRole("link", { name: "Continue" })).toHaveAttribute(
      "href",
      "/create/job-analysis?jd=jd-2",
    );
    expect(screen.getByRole("link", { name: "View history →" })).toHaveAttribute(
      "href",
      "/history",
    );
  });

  it("prompts to create the master resume when none exists", async () => {
    vi.mocked(fetchDashboard).mockResolvedValue({
      ...dashboard(),
      master_resume: null,
      recent_applications: [],
    });

    renderPage();

    expect(
      await screen.findByText(/No Master Resume yet\. Create one to start tailoring\./),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Create master" })).toHaveAttribute("href", "/resume");
    expect(screen.getByText(/No applications yet/)).toBeInTheDocument();
  });

  it("shows the structured error when the dashboard fails", async () => {
    vi.mocked(fetchDashboard).mockRejectedValue(new Error("backend unreachable"));

    renderPage();

    expect(await screen.findByText("backend unreachable")).toBeInTheDocument();
  });
});