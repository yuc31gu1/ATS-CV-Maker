import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fetchMatch } from "./match";

describe("fetchMatch", () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    globalThis.fetch = vi.fn();
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it("fetches the match result for a job description and resume", async () => {
    const match = {
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
          rationale: "Skill 'fastapi' is listed and substantiated.",
          evidence_ids: ["experience:0:bullet:0"],
          evidence: ["Built the ordering API with FastAPI"],
        },
      ],
    };
    vi.mocked(globalThis.fetch).mockResolvedValue(
      new Response(JSON.stringify(match), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    await expect(fetchMatch("jd-1", "resume-1")).resolves.toEqual(match);

    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/job-descriptions/jd-1/match?resume_id=resume-1"),
      expect.objectContaining({ signal: undefined }),
    );
  });

  it("omits the resume_id query param when no resume is provided", async () => {
    vi.mocked(globalThis.fetch).mockResolvedValue(
      new Response(JSON.stringify({ job_description_id: "jd-1" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    await fetchMatch("jd-1", null);

    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/job-descriptions/jd-1/match"),
      expect.anything(),
    );
    const url = vi.mocked(globalThis.fetch).mock.calls[0][0] as string;
    expect(url).not.toContain("resume_id");
  });

  it("throws the structured error message on failure", async () => {
    vi.mocked(globalThis.fetch).mockResolvedValue(
      new Response(
        JSON.stringify({ error: { code: "NOT_FOUND", message: "job analysis not found" } }),
        { status: 404, headers: { "Content-Type": "application/json" } },
      ),
    );

    await expect(fetchMatch("missing", null)).rejects.toThrow("job analysis not found");
  });
});