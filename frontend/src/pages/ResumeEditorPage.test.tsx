import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { Resume } from "../api/resume";
import { emptyResume } from "../domain/resume";
import { ResumeEditorPage } from "./ResumeEditorPage";

vi.mock("../api/resume", () => ({
  listResumes: vi.fn(),
  createResume: vi.fn(),
  updateResume: vi.fn(),
}));

import { createResume, listResumes, updateResume } from "../api/resume";

function savedResume(): Resume {
  return {
    ...emptyResume(),
    id: "resume-1",
    personal_information: {
      ...emptyResume().personal_information,
      full_name: "Ada Lovelace",
      email: "ada@example.com",
    },
    summary: "Deterministic document pipelines.",
    skills: { languages: ["Python"], frameworks: ["FastAPI"] },
    experience: [
      {
        company: "Analytical Engines Ltd",
        title: "Engineer",
        location: "London",
        start_date: "2021-03",
        end_date: "2024-05",
        summary: "",
        bullets: ["Shipped the PDF pipeline"],
      },
    ],
  };
}

describe("ResumeEditorPage", () => {
  afterEach(() => cleanup());

  beforeEach(() => {
    vi.mocked(listResumes).mockResolvedValue([savedResume()]);
    vi.mocked(createResume).mockResolvedValue({ ...savedResume(), id: "new-id" });
    vi.mocked(updateResume).mockResolvedValue(savedResume());
  });

  it("restores the saved master resume on load", async () => {
    render(<ResumeEditorPage />);

    const nameField = await screen.findByLabelText("Full name");
    expect(nameField).toHaveValue("Ada Lovelace");
    expect(screen.getByLabelText("Summary")).toHaveValue("Deterministic document pipelines.");
    expect(screen.getByLabelText("Company")).toHaveValue("Analytical Engines Ltd");
    expect(screen.getByLabelText("Start date")).toHaveValue("2021-03");
    expect(screen.getByLabelText("Bullets (one per line)")).toHaveValue("Shipped the PDF pipeline");
    expect(screen.getByLabelText("languages")).toHaveValue("Python");
    expect(screen.getByLabelText("frameworks")).toHaveValue("FastAPI");
  });

  it("supports editing a section and saving via updateResume", async () => {
    const user = userEvent.setup();
    render(<ResumeEditorPage />);

    const summaryField = await screen.findByLabelText("Summary");
    await user.clear(summaryField);
    await user.type(summaryField, "Rewritten summary");

    await user.click(screen.getByRole("button", { name: "Save" }));

    expect(updateResume).toHaveBeenCalledWith(
      "resume-1",
      expect.objectContaining({ id: "resume-1", summary: "Rewritten summary" }),
    );
    expect(await screen.findByText("Master resume saved.")).toBeInTheDocument();
  });

  it("creates a new master resume when none exists yet", async () => {
    vi.mocked(listResumes).mockResolvedValue([]);
    const user = userEvent.setup();
    render(<ResumeEditorPage />);

    const nameField = await screen.findByLabelText("Full name");
    await user.type(nameField, "Grace Hopper");

    await user.click(screen.getByRole("button", { name: "Save" }));

    expect(createResume).toHaveBeenCalledWith(
      expect.objectContaining({
        id: null,
        personal_information: expect.objectContaining({ full_name: "Grace Hopper" }),
      }),
    );
  });
});