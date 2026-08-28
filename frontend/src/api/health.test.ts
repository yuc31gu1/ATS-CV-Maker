import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fetchHealth } from "./health";

describe("fetchHealth", () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    globalThis.fetch = vi.fn();
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it("parses the health response", async () => {
    vi.mocked(globalThis.fetch).mockResolvedValue(
      new Response(
        JSON.stringify({
          status: "ok",
          service: "ats-cv-backend",
          database: { status: "unavailable" },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );

    await expect(fetchHealth()).resolves.toEqual({
      status: "ok",
      service: "ats-cv-backend",
      database: { status: "unavailable" },
    });
  });

  it("throws when the backend is not reachable", async () => {
    vi.mocked(globalThis.fetch).mockResolvedValue(new Response("oops", { status: 500 }));

    await expect(fetchHealth()).rejects.toThrow("Health check failed with status 500");
  });
});