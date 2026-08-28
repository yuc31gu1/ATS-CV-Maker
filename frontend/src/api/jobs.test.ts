import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fetchJob, fetchJobAnalysis, submitJobDescription } from "./jobs";

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