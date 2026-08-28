import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fetchApplications, type ApplicationSummary } from "../api/dashboard";
import { HistoryPage } from "./HistoryPage";

vi.mock("../api/dashboard", () => ({
  fetchApplications: vi.fn(),
}));

function application(): ApplicationSummary {
  return {
    job_description_id: "jd-1",
    company: "Acme",
    role: "Engineer",
    location: "Remote",
    created_at: "2026-08-28T12:00:00Z",
    has_analysis: true,
    has_tailored: true,
    has_generated: true,
  };
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/history"]}>
      <HistoryPage />
    </MemoryRouter>,
  );
}

describe("HistoryPage", () => {
  afterEach(() => cleanup());

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(fetchApplications).mockResolvedValue([
      application(),
      { ...application(), job_description_id: "jd-2", company: null, role: null, location: null, has_generated: false },
    ]);
  });

  it("lists prior applications with dates and stage badges", async () => {
    renderPage();

    expect(await screen.findByText(/Acme · Engineer · Remote/)).toBeInTheDocument();
    expect(screen.getByText(/Untitled application/)).toBeInTheDocument();
    expect(screen.getAllByText(/Analyzed/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Tailored/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Generated/).length).toBeGreaterThan(0);
  });

  it("reopens a generated CV and continues an in-progress one", async () => {
    renderPage();

    expect(
      await screen.findByRole("link", { name: "Reopen CV" }),
    ).toHaveAttribute("href", "/create/result?jd=jd-1");
    expect(screen.getByRole("link", { name: "Continue" })).toHaveAttribute(
      "href",
      "/create/job-analysis?jd=jd-2",
    );
  });

  it("links back to the dashboard", async () => {
    renderPage();

    expect(await screen.findByText(/Acme · Engineer · Remote/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /← Dashboard/ })).toHaveAttribute("href", "/dashboard");
  });

  it("shows an empty state when there are no applications", async () => {
    vi.mocked(fetchApplications).mockResolvedValue([]);

    renderPage();

    expect(await screen.findByText(/No applications yet/)).toBeInTheDocument();
  });

  it("shows the structured error when history fails", async () => {
    vi.mocked(fetchApplications).mockRejectedValue(new Error("history unavailable"));

    renderPage();

    expect(await screen.findByText("history unavailable")).toBeInTheDocument();
  });
});