import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fetchApplications, fetchDashboard } from "./dashboard";

describe("fetchDashboard", () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    globalThis.fetch = vi.fn();
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it("parses the dashboard summary", async () => {
    vi.mocked(globalThis.fetch).mockResolvedValue(
      new Response(
        JSON.stringify({
          master_resume: {
            id: "resume-1",
            schema_version: 1,
            personal_information: { full_name: "Ada Lovelace" },
            summary: "",
            skills: {},
            experience: [],
            education: [],
            projects: [],
            certifications: [],
          },
          tailored_cv_count: 2,
          analyzed_jobs_count: 3,
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
          ],
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );

    await expect(fetchDashboard()).resolves.toMatchObject({
      tailored_cv_count: 2,
      analyzed_jobs_count: 3,
      recent_applications: [{ job_description_id: "jd-1", has_generated: true }],
    });
    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/dashboard"),
      expect.anything(),
    );
  });

  it("throws the structured error message on failure", async () => {
    vi.mocked(globalThis.fetch).mockResolvedValue(
      new Response(
        JSON.stringify({ error: { code: "INTERNAL_ERROR", message: "boom" } }),
        { status: 500, headers: { "Content-Type": "application/json" } },
      ),
    );

    await expect(fetchDashboard()).rejects.toThrow("boom");
  });
});

describe("fetchApplications", () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    globalThis.fetch = vi.fn();
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it("parses the applications list", async () => {
    vi.mocked(globalThis.fetch).mockResolvedValue(
      new Response(
        JSON.stringify([
          {
            job_description_id: "jd-1",
            company: "Acme",
            role: "Engineer",
            location: "Remote",
            created_at: "2026-08-28T12:00:00Z",
            has_analysis: false,
            has_tailored: false,
            has_generated: false,
          },
        ]),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );

    await expect(fetchApplications()).resolves.toEqual([
      {
        job_description_id: "jd-1",
        company: "Acme",
        role: "Engineer",
        location: "Remote",
        created_at: "2026-08-28T12:00:00Z",
        has_analysis: false,
        has_tailored: false,
        has_generated: false,
      },
    ]);
  });
});