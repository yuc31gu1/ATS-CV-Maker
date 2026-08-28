import { useEffect, useState, type ReactNode } from "react";
import {
  createResume,
  listResumes,
  updateResume,
  type Certification,
  type Education,
  type Experience,
  type Project,
  type Resume,
} from "../api/resume";
import { emptyResume, renderMonthYear } from "../domain/resume";

const SKILL_CATEGORIES = ["languages", "frameworks", "tools", "domains"];

type LoadState =
  | { phase: "loading" }
  | { phase: "ready" }
  | { phase: "error"; message: string };

type SaveState = { phase: "idle" } | { phase: "saving" } | { phase: "saved" };

function splitLines(value: string): string[] {
  return value
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
}

function splitCsv(value: string): string[] {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

export function ResumeEditorPage() {
  const [resume, setResume] = useState<Resume>(() => emptyResume());
  const [loadState, setLoadState] = useState<LoadState>({ phase: "loading" });
  const [saveState, setSaveState] = useState<SaveState>({ phase: "idle" });

  useEffect(() => {
    const controller = new AbortController();
    listResumes(controller.signal)
      .then((resumes) => {
        setResume(resumes[0] ?? emptyResume());
        setLoadState({ phase: "ready" });
      })
      .catch((err: unknown) => {
        if (err instanceof Error && err.name === "AbortError") {
          return;
        }
        setLoadState({
          phase: "error",
          message: err instanceof Error ? err.message : String(err),
        });
      });
    return () => controller.abort();
  }, []);

  function update(fn: (prev: Resume) => Resume) {
    setResume((prev) => fn(prev));
  }

  async function handleSave() {
    setSaveState({ phase: "saving" });
    try {
      const saved =
        resume.id === null ? await createResume(resume) : await updateResume(resume.id, resume);
      setResume(saved);
      setSaveState({ phase: "saved" });
    } catch (err: unknown) {
      setSaveState({ phase: "idle" });
      alert(err instanceof Error ? err.message : String(err));
    }
  }

  if (loadState.phase === "loading") {
    return <main className="p-8 text-slate-500">Loading master resume…</main>;
  }

  if (loadState.phase === "error") {
    return (
      <main className="p-8">
        <p className="text-red-600">Failed to load master resume: {loadState.message}</p>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-3xl space-y-8 bg-slate-50 p-8">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Master Resume</h1>
          <p className="text-sm text-slate-500">
            The canonical source of truth. Never mutated by tailoring or generation.
          </p>
        </div>
        <button
          type="button"
          onClick={handleSave}
          disabled={saveState.phase === "saving"}
          className="rounded-lg bg-blue-600 px-4 py-2 font-medium text-white disabled:opacity-50"
        >
          {saveState.phase === "saving" ? "Saving…" : "Save"}
        </button>
      </header>

      {saveState.phase === "saved" && (
        <p className="rounded-md bg-green-50 p-3 text-sm text-green-700">Master resume saved.</p>
      )}

      <PersonalInformationSection resume={resume} update={update} />
      <SummarySection resume={resume} update={update} />
      <SkillsSection resume={resume} update={update} />
      <ExperienceSection resume={resume} update={update} />
      <EducationSection resume={resume} update={update} />
      <ProjectsSection resume={resume} update={update} />
      <CertificationsSection resume={resume} update={update} />
    </main>
  );
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <h2 className="mb-4 text-lg font-semibold text-slate-900">{title}</h2>
      {children}
    </section>
  );
}

function TextField({
  label,
  value,
  onChange,
  placeholder,
  type = "text",
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  type?: string;
}) {
  return (
    <label className="block">
      <span className="text-sm font-medium text-slate-700">{label}</span>
      <input
        type={type}
        value={value}
        placeholder={placeholder}
        onChange={(event) => onChange(event.target.value)}
        className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
      />
    </label>
  );
}

function PersonalInformationSection({
  resume,
  update,
}: {
  resume: Resume;
  update: (fn: (prev: Resume) => Resume) => void;
}) {
  const info = resume.personal_information;
  return (
    <Section title="Personal information">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <TextField
          label="Full name"
          value={info.full_name}
          onChange={(full_name) => update((r) => ({ ...r, personal_information: { ...r.personal_information, full_name } }))}
        />
        <TextField
          label="Headline"
          value={info.headline}
          onChange={(headline) => update((r) => ({ ...r, personal_information: { ...r.personal_information, headline } }))}
        />
        <TextField
          label="Email"
          type="email"
          value={info.email}
          onChange={(email) => update((r) => ({ ...r, personal_information: { ...r.personal_information, email } }))}
        />
        <TextField
          label="Phone"
          value={info.phone}
          onChange={(phone) => update((r) => ({ ...r, personal_information: { ...r.personal_information, phone } }))}
        />
        <TextField
          label="Location"
          value={info.location}
          onChange={(location) => update((r) => ({ ...r, personal_information: { ...r.personal_information, location } }))}
        />
        <TextField
          label="Website"
          value={info.website}
          onChange={(website) => update((r) => ({ ...r, personal_information: { ...r.personal_information, website } }))}
        />
      </div>
    </Section>
  );
}

function SummarySection({ resume, update }: { resume: Resume; update: (fn: (prev: Resume) => Resume) => void }) {
  return (
    <Section title="Summary">
      <label className="block">
        <span className="text-sm font-medium text-slate-700">Summary</span>
        <textarea
          value={resume.summary}
          onChange={(event) => update((r) => ({ ...r, summary: event.target.value }))}
          rows={4}
          className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
        />
      </label>
    </Section>
  );
}

function SkillsSection({ resume, update }: { resume: Resume; update: (fn: (prev: Resume) => Resume) => void }) {
  return (
    <Section title="Skills">
      <div className="space-y-3">
        {SKILL_CATEGORIES.map((category) => (
          <label key={category} className="block">
            <span className="text-sm font-medium text-slate-700 capitalize">{category}</span>
            <input
              value={(resume.skills[category] ?? []).join(", ")}
              onChange={(event) =>
                update((r) => ({
                  ...r,
                  skills: { ...r.skills, [category]: splitCsv(event.target.value) },
                }))
              }
              placeholder="Comma-separated canonical skills"
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            />
          </label>
        ))}
      </div>
    </Section>
  );
}

function ExperienceSection({ resume, update }: { resume: Resume; update: (fn: (prev: Resume) => Resume) => void }) {
  return (
    <Section title="Experience">
      <div className="space-y-6">
        {resume.experience.map((experience, index) => (
          <div key={index} className="rounded-md border border-slate-200 p-4">
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <TextField
                label="Company"
                value={experience.company}
                onChange={(company) => update((r) => updateExperience(r, index, { company }))}
              />
              <TextField
                label="Title"
                value={experience.title}
                onChange={(title) => update((r) => updateExperience(r, index, { title }))}
              />
              <TextField
                label="Location"
                value={experience.location}
                onChange={(location) => update((r) => updateExperience(r, index, { location }))}
              />
              <TextField
                label="Start date"
                placeholder="YYYY-MM"
                value={experience.start_date}
                onChange={(start_date) => update((r) => updateExperience(r, index, { start_date }))}
              />
              <TextField
                label="End date (blank if current)"
                placeholder="YYYY-MM"
                value={experience.end_date ?? ""}
                onChange={(value) =>
                  update((r) => updateExperience(r, index, { end_date: value || null }))
                }
              />
            </div>
            <label className="mt-3 block">
              <span className="text-sm font-medium text-slate-700">Bullets (one per line)</span>
              <textarea
                value={experience.bullets.join("\n")}
                onChange={(event) =>
                  update((r) => updateExperience(r, index, { bullets: splitLines(event.target.value) }))
                }
                rows={3}
                className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
              />
            </label>
            <div className="mt-3 flex items-center justify-between">
              <span className="text-xs text-slate-400">
                {experience.start_date && renderMonthYear(experience.start_date)}
              </span>
              <RemoveButton
                label="Remove experience"
                onClick={() => update((r) => ({ ...r, experience: r.experience.filter((_, i) => i !== index) }))}
              />
            </div>
          </div>
        ))}
        <AddButton
          label="Add experience"
          onClick={() =>
            update((r) => ({
              ...r,
              experience: [...r.experience, emptyExperience()],
            }))
          }
        />
      </div>
    </Section>
  );
}

function updateExperience(resume: Resume, index: number, patch: Partial<Experience>): Resume {
  return {
    ...resume,
    experience: resume.experience.map((experience, i) =>
      i === index ? { ...experience, ...patch } : experience,
    ),
  };
}

function emptyExperience(): Experience {
  return {
    company: "",
    title: "",
    location: "",
    start_date: "",
    end_date: null,
    summary: "",
    bullets: [],
  };
}

function EducationSection({ resume, update }: { resume: Resume; update: (fn: (prev: Resume) => Resume) => void }) {
  return (
    <Section title="Education">
      <div className="space-y-6">
        {resume.education.map((education, index) => (
          <div key={index} className="rounded-md border border-slate-200 p-4">
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <TextField
                label="School"
                value={education.school}
                onChange={(school) =>
                  update((r) => ({
                    ...r,
                    education: r.education.map((e, i) => (i === index ? { ...e, school } : e)),
                  }))
                }
              />
              <TextField
                label="Degree"
                value={education.degree}
                onChange={(degree) =>
                  update((r) => ({
                    ...r,
                    education: r.education.map((e, i) => (i === index ? { ...e, degree } : e)),
                  }))
                }
              />
              <TextField
                label="Field"
                value={education.field}
                onChange={(field) =>
                  update((r) => ({
                    ...r,
                    education: r.education.map((e, i) => (i === index ? { ...e, field } : e)),
                  }))
                }
              />
              <TextField
                label="Location"
                value={education.location}
                onChange={(location) =>
                  update((r) => ({
                    ...r,
                    education: r.education.map((e, i) => (i === index ? { ...e, location } : e)),
                  }))
                }
              />
              <TextField
                label="Start date"
                placeholder="YYYY-MM"
                value={education.start_date}
                onChange={(start_date) =>
                  update((r) => ({
                    ...r,
                    education: r.education.map((e, i) => (i === index ? { ...e, start_date } : e)),
                  }))
                }
              />
              <TextField
                label="End date (blank if current)"
                placeholder="YYYY-MM"
                value={education.end_date ?? ""}
                onChange={(value) =>
                  update((r) => ({
                    ...r,
                    education: r.education.map((e, i) =>
                      i === index ? { ...e, end_date: value || null } : e,
                    ),
                  }))
                }
              />
            </div>
            <RemoveButton
              label="Remove education"
              onClick={() =>
                update((r) => ({ ...r, education: r.education.filter((_, i) => i !== index) }))
              }
            />
          </div>
        ))}
        <AddButton
          label="Add education"
          onClick={() =>
            update((r) => ({ ...r, education: [...r.education, emptyEducation()] }))
          }
        />
      </div>
    </Section>
  );
}

function emptyEducation(): Education {
  return {
    school: "",
    degree: "",
    field: "",
    location: "",
    start_date: "",
    end_date: null,
  };
}

function ProjectsSection({ resume, update }: { resume: Resume; update: (fn: (prev: Resume) => Resume) => void }) {
  return (
    <Section title="Projects">
      <div className="space-y-6">
        {resume.projects.map((project, index) => (
          <div key={index} className="rounded-md border border-slate-200 p-4">
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <TextField
                label="Name"
                value={project.name}
                onChange={(name) => update((r) => updateProject(r, index, { name }))}
              />
              <TextField
                label="URL"
                value={project.url}
                onChange={(url) => update((r) => updateProject(r, index, { url }))}
              />
            </div>
            <label className="mt-3 block">
              <span className="text-sm font-medium text-slate-700">Description</span>
              <textarea
                value={project.description}
                onChange={(event) =>
                  update((r) => updateProject(r, index, { description: event.target.value }))
                }
                rows={2}
                className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
              />
            </label>
            <label className="mt-3 block">
              <span className="text-sm font-medium text-slate-700">Technologies (comma-separated)</span>
              <input
                value={project.technologies.join(", ")}
                onChange={(event) =>
                  update((r) => updateProject(r, index, { technologies: splitCsv(event.target.value) }))
                }
                className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
              />
            </label>
            <label className="mt-3 block">
              <span className="text-sm font-medium text-slate-700">Bullets (one per line)</span>
              <textarea
                value={project.bullets.join("\n")}
                onChange={(event) =>
                  update((r) => updateProject(r, index, { bullets: splitLines(event.target.value) }))
                }
                rows={2}
                className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
              />
            </label>
            <RemoveButton
              label="Remove project"
              onClick={() =>
                update((r) => ({ ...r, projects: r.projects.filter((_, i) => i !== index) }))
              }
            />
          </div>
        ))}
        <AddButton
          label="Add project"
          onClick={() => update((r) => ({ ...r, projects: [...r.projects, emptyProject()] }))}
        />
      </div>
    </Section>
  );
}

function updateProject(resume: Resume, index: number, patch: Partial<Project>): Resume {
  return {
    ...resume,
    projects: resume.projects.map((project, i) => (i === index ? { ...project, ...patch } : project)),
  };
}

function emptyProject(): Project {
  return {
    name: "",
    description: "",
    url: "",
    technologies: [],
    bullets: [],
  };
}

function CertificationsSection({ resume, update }: { resume: Resume; update: (fn: (prev: Resume) => Resume) => void }) {
  return (
    <Section title="Certifications">
      <div className="space-y-6">
        {resume.certifications.map((certification, index) => (
          <div key={index} className="rounded-md border border-slate-200 p-4">
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <TextField
                label="Name"
                value={certification.name}
                onChange={(name) => update((r) => updateCertification(r, index, { name }))}
              />
              <TextField
                label="Issuer"
                value={certification.issuer}
                onChange={(issuer) => update((r) => updateCertification(r, index, { issuer }))}
              />
              <TextField
                label="Date"
                placeholder="YYYY-MM"
                value={certification.date}
                onChange={(date) => update((r) => updateCertification(r, index, { date }))}
              />
              <TextField
                label="URL"
                value={certification.url}
                onChange={(url) => update((r) => updateCertification(r, index, { url }))}
              />
            </div>
            <RemoveButton
              label="Remove certification"
              onClick={() =>
                update((r) => ({
                  ...r,
                  certifications: r.certifications.filter((_, i) => i !== index),
                }))
              }
            />
          </div>
        ))}
        <AddButton
          label="Add certification"
          onClick={() =>
            update((r) => ({ ...r, certifications: [...r.certifications, emptyCertification()] }))
          }
        />
      </div>
    </Section>
  );
}

function updateCertification(resume: Resume, index: number, patch: Partial<Certification>): Resume {
  return {
    ...resume,
    certifications: resume.certifications.map((certification, i) =>
      i === index ? { ...certification, ...patch } : certification,
    ),
  };
}

function emptyCertification(): Certification {
  return { name: "", issuer: "", date: "", url: "" };
}

function AddButton({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="rounded-md border border-blue-300 px-3 py-1.5 text-sm font-medium text-blue-700"
    >
      {label}
    </button>
  );
}

function RemoveButton({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="rounded-md border border-red-200 px-3 py-1.5 text-sm font-medium text-red-600"
    >
      {label}
    </button>
  );
}