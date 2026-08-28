import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fetchJob, fetchJobAnalysis, fetchJobDescription, listJobs, submitJobDescription } from "./jobs";

describe("submitJobDescription", () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    globalThis.fetch = vi.fn();
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it("posts the job description and parses the submit response", async () => {
    vi.mocked(globalThis.fetch).mockResolvedValue(
      new Response(
        JSON.stringify({
          job_description_id: "jd-1",
          job_id: "job-1",
          status: "PENDING",
        }),
        { status: 201, headers: { "Content-Type": "application/json" } },
      ),
    );

    await expect(
      submitJobDescription({ company: "Acme", jd_text: "Role: Engineer\n- Python" }),
    ).resolves.toEqual({
      job_description_id: "jd-1",
      job_id: "job-1",
      status: "PENDING",
    });

    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/job-descriptions"),
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ company: "Acme", jd_text: "Role: Engineer\n- Python" }),
      }),
    );
  });

  it("throws the structured error message on failure", async () => {
    vi.mocked(globalThis.fetch).mockResolvedValue(
      new Response(
        JSON.stringify({ error: { code: "VALIDATION_ERROR", message: "text required" } }),
        { status: 422, headers: { "Content-Type": "application/json" } },
      ),
    );

    await expect(submitJobDescription({ jd_text: "" })).rejects.toThrow("text required");
  });
});

describe("fetchJob", () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    globalThis.fetch = vi.fn();
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it("parses the polled job status", async () => {
    vi.mocked(globalThis.fetch).mockResolvedValue(
      new Response(
        JSON.stringify({
          id: "job-1",
          type: "ANALYZE",
          status: "SUCCEEDED",
          result: { role: "Engineer" },
          error: null,
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );

    await expect(fetchJob("job-1")).resolves.toEqual({
      id: "job-1",
      type: "ANALYZE",
      status: "SUCCEEDED",
      result: { role: "Engineer" },
      error: null,
    });
  });
});

describe("fetchJobAnalysis", () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    globalThis.fetch = vi.fn();
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it("parses the job analysis", async () => {
    vi.mocked(globalThis.fetch).mockResolvedValue(
      new Response(
        JSON.stringify({
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
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );

    await expect(fetchJobAnalysis("jd-1")).resolves.toEqual({
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
    });
  });
});

describe("fetchJobDescription", () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    globalThis.fetch = vi.fn();
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it("fetches and parses a stored job description", async () => {
    vi.mocked(globalThis.fetch).mockResolvedValue(
      new Response(
        JSON.stringify({
          id: "jd-1",
          company: "Acme",
          role: "Engineer",
          location: "Remote",
          jd_text: "Role: Engineer\n- Python",
          created_at: "2026-08-28T12:00:00Z",
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );

    await expect(fetchJobDescription("jd-1")).resolves.toEqual({
      id: "jd-1",
      company: "Acme",
      role: "Engineer",
      location: "Remote",
      jd_text: "Role: Engineer\n- Python",
      created_at: "2026-08-28T12:00:00Z",
    });
    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/job-descriptions/jd-1"),
      expect.anything(),
    );
  });
});

describe("listJobs", () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    globalThis.fetch = vi.fn();
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it("lists jobs filtered by type and job description id", async () => {
    vi.mocked(globalThis.fetch).mockResolvedValue(
      new Response(
        JSON.stringify([
          { id: "job-1", type: "ANALYZE", status: "RUNNING", result: null, error: null },
        ]),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );

    await expect(listJobs("ANALYZE", "jd-1")).resolves.toEqual([
      { id: "job-1", type: "ANALYZE", status: "RUNNING", result: null, error: null },
    ]);

    const url = vi.mocked(globalThis.fetch).mock.calls[0][0] as string;
    expect(url).toContain("/jobs");
    expect(url).toContain("type=ANALYZE");
    expect(url).toContain("job_description_id=jd-1");
  });
});