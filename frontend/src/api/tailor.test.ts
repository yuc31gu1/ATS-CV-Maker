import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  fetchTailored,
  submitRegenerate,
  submitReviewDecisions,
  submitTailor,
} from "./tailor";

describe("tailor API", () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    globalThis.fetch = vi.fn();
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it("starts a TAILOR job for a resume and job description", async () => {
    const response = {
      job_id: "job-1",
      job_description_id: "jd-1",
      resume_id: "resume-1",
      status: "PENDING",
    };
    vi.mocked(globalThis.fetch).mockResolvedValue(
      new Response(JSON.stringify(response), { status: 201 }),
    );

    await expect(submitTailor("resume-1", "jd-1")).resolves.toEqual(response);

    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/resumes/resume-1/tailor"),
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ job_description_id: "jd-1" }),
      }),
    );
  });

  it("fetches the staged tailored resume", async () => {
    const tailored = { job_description_id: "jd-1", summary: "Summary", changes: [] };
    vi.mocked(globalThis.fetch).mockResolvedValue(
      new Response(JSON.stringify(tailored), { status: 200 }),
    );

    await expect(fetchTailored("jd-1")).resolves.toEqual(tailored);
    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/job-descriptions/jd-1/tailored"),
      expect.anything(),
    );
  });

  it("submits review decisions", async () => {
    const tailored = { job_description_id: "jd-1", changes: [] };
    vi.mocked(globalThis.fetch).mockResolvedValue(
      new Response(JSON.stringify(tailored), { status: 200 }),
    );

    await submitReviewDecisions("jd-1", [
      { key: "summary", action: "accept" },
      { key: "experience:0:bullet:0", action: "reject" },
    ]);

    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/job-descriptions/jd-1/tailored/decisions"),
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          decisions: [
            { key: "summary", action: "accept" },
            { key: "experience:0:bullet:0", action: "reject" },
          ],
        }),
      }),
    );
  });

  it("requests regeneration of one change", async () => {
    const response = { job_id: "job-2", job_description_id: "jd-1", resume_id: "resume-1", status: "PENDING" };
    vi.mocked(globalThis.fetch).mockResolvedValue(
      new Response(JSON.stringify(response), { status: 201 }),
    );

    await expect(submitRegenerate("jd-1", "summary")).resolves.toEqual(response);
    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/job-descriptions/jd-1/tailored/regenerate"),
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ change_key: "summary" }),
      }),
    );
  });

  it("throws the structured error message on failure", async () => {
    vi.mocked(globalThis.fetch).mockResolvedValue(
      new Response(
        JSON.stringify({ error: { code: "NOT_FOUND", message: "tailored resume not found" } }),
        { status: 404 },
      ),
    );

    await expect(fetchTailored("missing")).rejects.toThrow("tailored resume not found");
  });
});