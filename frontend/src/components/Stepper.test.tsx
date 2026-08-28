import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it } from "vitest";
import { Stepper, type StepKey } from "./Stepper";

function renderStepper(current: StepKey, jobDescriptionId: string | null) {
  return render(
    <MemoryRouter initialEntries={["/"]}>
      <Stepper current={current} jobDescriptionId={jobDescriptionId} />
    </MemoryRouter>,
  );
}

describe("Stepper", () => {
  afterEach(() => cleanup());

  it("shows all eight steps and highlights the current one", () => {
    renderStepper("analysis", "jd-1");

    const nav = screen.getByRole("navigation", { name: "Create flow" });
    expect(nav).toBeInTheDocument();
    for (const label of ["Master CV", "Job", "Analysis", "Match", "Generate", "Review", "ATS", "Export"]) {
      expect(screen.getByText(label)).toBeInTheDocument();
    }
  });

  it("links reached steps through the session id", () => {
    renderStepper("match", "jd-1");

    expect(screen.getByRole("link", { name: "Master CV" })).toHaveAttribute("href", "/resume");
    expect(screen.getByRole("link", { name: "Analysis" })).toHaveAttribute(
      "href",
      "/create/job-analysis?jd=jd-1",
    );
    expect(screen.getByRole("link", { name: "Generate" })).toHaveAttribute(
      "href",
      "/create/review?jd=jd-1",
    );
    expect(screen.getByRole("link", { name: "ATS" })).toHaveAttribute(
      "href",
      "/create/result?jd=jd-1",
    );
  });

  it("keeps later steps inert without a session id", () => {
    renderStepper("job", null);

    expect(screen.queryByRole("link", { name: "Match" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Export" })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Master CV" })).toHaveAttribute("href", "/resume");
  });
});