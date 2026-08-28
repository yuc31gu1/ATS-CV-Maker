import { describe, expect, it } from "vitest";
import { emptyResume, renderMonthYear } from "./resume";

describe("renderMonthYear", () => {
  it("renders YYYY-MM as a month name and year", () => {
    expect(renderMonthYear("2024-05")).toBe("May 2024");
    expect(renderMonthYear("2020-01")).toBe("January 2020");
  });

  it("passes through values that are not YYYY-MM", () => {
    expect(renderMonthYear("present")).toBe("present");
    expect(renderMonthYear("")).toBe("");
  });
});

describe("emptyResume", () => {
  it("returns a blank, structured resume", () => {
    const resume = emptyResume();
    expect(resume.id).toBeNull();
    expect(resume.schema_version).toBe(1);
    expect(resume.personal_information.full_name).toBe("");
    expect(resume.skills).toEqual({});
    expect(resume.experience).toEqual([]);
    expect(resume.education).toEqual([]);
    expect(resume.projects).toEqual([]);
    expect(resume.certifications).toEqual([]);
  });

  it("returns a fresh object each call", () => {
    const first = emptyResume();
    const second = emptyResume();
    first.personal_information.full_name = "Ada";
    expect(second.personal_information.full_name).toBe("");
  });
});