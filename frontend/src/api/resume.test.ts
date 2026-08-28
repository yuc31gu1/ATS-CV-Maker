import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { emptyResume } from "../domain/resume";
import {
  createResume,
  getResume,
  listResumes,
  updateResume,
  type Resume,
} from "./resume";

describe("resume api", () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    globalThis.fetch = vi.fn();
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  function mockResume(overrides: Partial<Resume> = {}): Resume {
    return { ...emptyResume(), id: "resume-1", ...overrides };
  }

  it("lists resumes", async () => {
    vi.mocked(globalThis.fetch).mockResolvedValue(
      new Response(JSON.stringify([mockResume()]), { status: 200 }),
    );
    await expect(listResumes()).resolves.toEqual([mockResume()]);
    expect(globalThis.fetch).toHaveBeenCalledWith("/api/resumes", { signal: undefined });
  });

  it("fetches a single resume", async () => {
    vi.mocked(globalThis.fetch).mockResolvedValue(
      new Response(JSON.stringify(mockResume()), { status: 200 }),
    );
    await expect(getResume("resume-1")).resolves.toEqual(mockResume());
    expect(globalThis.fetch).toHaveBeenCalledWith("/api/resumes/resume-1", {
      signal: undefined,
    });
  });

  it("creates a resume with a POST", async () => {
    vi.mocked(globalThis.fetch).mockResolvedValue(
      new Response(JSON.stringify(mockResume({ id: "new-id" })), { status: 201 }),
    );
    const result = await createResume(mockResume());
    expect(result.id).toBe("new-id");
    expect(globalThis.fetch).toHaveBeenCalledWith(
      "/api/resumes",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("updates a resume with a PUT", async () => {
    vi.mocked(globalThis.fetch).mockResolvedValue(
      new Response(JSON.stringify(mockResume({ summary: "Updated" })), { status: 200 }),
    );
    const result = await updateResume("resume-1", mockResume({ summary: "Updated" }));
    expect(result.summary).toBe("Updated");
    expect(globalThis.fetch).toHaveBeenCalledWith(
      "/api/resumes/resume-1",
      expect.objectContaining({ method: "PUT" }),
    );
  });

  it("surfaces the structured error message on 422", async () => {
    vi.mocked(globalThis.fetch).mockResolvedValue(
      new Response(
        JSON.stringify({ error: { code: "INVALID_RESUME", message: "invalid resume" } }),
        { status: 422 },
      ),
    );
    await expect(createResume(mockResume())).rejects.toThrow("invalid resume");
  });

  it("falls back to a status message for non-JSON errors", async () => {
    vi.mocked(globalThis.fetch).mockResolvedValue(new Response("oops", { status: 500 }));
    await expect(getResume("nope")).rejects.toThrow("Request failed with status 500");
  });
});