# ATS CV Maker — Product Spec

Canonical copy of the product spec tracked as issue #1 (`yuc31gu1/ATS-CV-Maker`). The domain glossary in `CONTEXT.md` governs vocabulary; architecture decisions live in `docs/adr/` (ADR-0001–0004). Implementation proceeds in phases T1–T8 (see [Phase plan](#phase-plan)).

## Problem Statement

Job applicants spend hours manually re-tailoring their CV to each job posting, and when they use AI to help, they get either a prettier-but-unsafe template or a resume with invented experience. Recruiters and ATS parsers reject both. The applicant needs a tool that produces a truthful, job-specific, ATS-safe CV from a single source of truth — and can prove, transparently, why every claim and every layout choice was made.

## Solution

A full-stack web application: the user maintains one canonical Master Resume, pastes a Job Description, and the system produces a job-specific Tailored Resume rendered as an ATS-optimized PDF plus LaTeX source, with a transparent analysis of requirement coverage, candidate evidence matching, and PDF machine-readability.

The system is built as a deterministic document pipeline. The LLM controls content (extracting job requirements, rewriting evidence-backed wording) but never controls structure, layout, or output validity. A deterministic Tailoring Engine decides what evidence survives and in what order; a deterministic LaTeX renderer owns formatting; a PDF validator gates every output. Nothing is ever fabricated: every claim in the final CV traces back to evidence in the Master Resume.

## User Stories

1. As a job applicant, I want to create a Master Resume once, so that it serves as the single source of truth for all tailored CVs.
2. As a job applicant, I want to edit and save any section of my Master Resume, so that my source data stays current.
3. As a job applicant, I want to import an existing resume, so that I don't have to type everything from scratch.
4. As a job applicant, I want my Master Resume to be structured (personal info, summary, skills, experience, education, projects, certifications), so that the pipeline can reason about it precisely.
5. As a job applicant, I want my Master Resume to never be mutated by tailoring, so that I can generate many versions without losing my canonical data.
6. As a job applicant, I want to paste a Job Description with company, role, and location, so that the system can analyze the exact target role.
7. As a job applicant, I want the system to extract the role, seniority, required skills, preferred skills, responsibilities, seniority signals, domain requirements, and soft skills from a JD, so that I can see what the job actually demands.
8. As a job applicant, I want every important JD requirement classified as REQUIRED / PREFERRED / RESPONSIBILITY / SENIORITY / DOMAIN / SOFT_SKILL with HIGH/MEDIUM/LOW importance, so that tailoring prioritizes the right things.
9. As a job applicant, I want the system to preserve JD context rather than reduce it to a keyword list, so that nuanced requirements are not lost.
10. As a job applicant, I want every requirement matched against evidence in my Master Resume with a status of STRONG_MATCH, PARTIAL_MATCH, TRANSFERABLE, or NO_EVIDENCE, so that I can see my real gaps.
11. As a job applicant, I want match statuses computed deterministically from a curated skill catalog, so that the results are auditable and never invented.
12. As a job applicant, I want ambiguous or adjacent technologies surfaced for my review rather than silently auto-resolved, so that no false equivalence (e.g. FastAPI vs Flask) is assumed.
13. As a job applicant, I want transferable knowledge clearly marked as transferable and never presented as direct experience, so that my CV stays truthful.
14. As a job applicant, I want the tailoring engine to decide which evidence survives, its order, and which JD terminology is genuinely supported, so that the strongest truthful content surfaces.
15. As a job applicant, I want the LLM to rewrite the summary and selected bullets inside the engine-selected scope, so that wording is job-targeted but content is evidence-bound.
16. As a job applicant, I want a verification gate that rejects any generated claim not traceable to source evidence, so that no fabricated technology, metric, employer, or responsibility ships.
17. As a job applicant, I want to review every change (original / tailored / reason) and accept, reject, regenerate, or edit it, so that I stay in control of my CV.
18. As a job applicant, I want the system to use the ACTION + WHAT + TECHNOLOGY + RESULT bullet pattern only when the result is backed by evidence, so that impact claims are real.
19. As a job applicant, I want a deterministic LaTeX renderer that owns all layout, so that the output is machine-parseable regardless of content.
20. As a job applicant, I want an ATS-safe single-column layout with standard section headings, so that parsers read my CV correctly.
21. As a job applicant, I want contact information in the document body, so that it survives extraction.
22. As a job applicant, I want consistent month-year date formatting, so that the CV looks professional.
23. As a job applicant, I want my content properly escaped before insertion into LaTeX, so that special characters never break compilation.
24. As a job applicant, I want PDF compilation isolated with timeouts and no arbitrary shell access, so that untrusted input is safe.
25. As a job applicant, I want every generated PDF validated by extracting its text and checking name, contact info, headings, experience, education, skills, and reading order, so that a broken PDF is never presented as final.
26. As a job applicant, I want the result presented as an "ATS Compatibility Analysis" with measured checks, not a fake percentage score, so that I get honest, useful signal.
27. As a job applicant, I want required/preferred keyword coverage and evidence coverage calculated over high-priority requirements, so that I can see where I stand.
28. As a job applicant, I want a stepper that persists state at every step and never loses my work when I navigate backward, so that long sessions are safe.
29. As a job applicant, I want to preview the actual generated PDF with zoom and page switching, so that what I download is what I reviewed.
30. As a job applicant, I want to download both the PDF and the LaTeX source, so that I can reuse or customize the output.
31. As a job applicant, I want a history of past applications and generated resumes I can reopen, so that I can compare or reuse them.
32. As a job applicant, I want every generated resume to be a version pinned to a snapshot of my master, so that history stays reproducible even if my master changes later.
33. As a job applicant, I want the pages count of my CV reported honestly (1 page early-career, up to 2 for experienced, never shrunk to fit), so that quality is not sacrificed for page count.
34. As a job applicant, I want a dashboard showing my master CV, number of tailored CVs and analyzed jobs, recent applications, and a "Create Tailored CV" action, so that I can resume work quickly.
35. As an operator, I want structured error codes from the API, so that failures are diagnosable without exposing stack traces.
36. As a developer, I want the pipeline split across API / application services / domain / repositories / database, so that each responsibility is testable in isolation.
37. As a developer, I want an LLM abstraction with structured output and validation, so that providers are swappable and bad model output fails cleanly.
38. As a developer, I want background jobs for heavy LLM stages and synchronous endpoints for fast deterministic stages, so that UX is responsive without unnecessary infrastructure.
39. As a developer, I want everything Dockerized (frontend, backend, postgres) with the backend image carrying LaTeX tooling, so that the stack runs anywhere.
40. As a developer, I want the full acceptance flow to pass end-to-end with a fixture provider, so that the product works deterministically without an LLM key.

## Implementation Decisions

Architecture boundary (ADR-0001): the LLM analyzes the JD, matches evidence, and rewrites content; it never produces the final document. The deterministic Tailoring Engine selects and orders evidence; a deterministic LaTeX renderer owns all layout; a PDF validator gates output. This preserves the spec's non-negotiable boundary.

Matching (ADR-0002): STRONG_MATCH / PARTIAL_MATCH / TRANSFERABLE / NO_EVIDENCE are assigned by deterministic rules over a curated, checked-in Skill Catalog. Synonyms (`AWS` = `Amazon Web Services`) resolve within the catalog; distinct-but-adjacent technologies (FastAPI vs Flask) are marked related, not synonyms, and are surfaced for human review. The LLM extracts requirements and may add a one-line rationale, but never assigns statuses.

Background jobs (ADR-0003): ANALYZE and TAILOR run as typed background jobs in-process against a generic `Job` table in Postgres, polled by the frontend. MATCH and GENERATE run synchronously. No Redis.

Versioning (ADR-0004): the Master Resume is edited in place; an immutable ResumeVersion snapshot is captured when a tailoring job starts. Every Generated Resume pins to a ResumeVersion, never to the live master.

Resume model: fully typed Pydantic entities for Experience, Education, Project, Certification, and Personal Information. Dates are MonthYear value objects (store YYYY-MM, render "May 2024"). Skills are a categorized dict of canonical skill names. Top-level schema_version with forward compatibility. Deterministic evidence IDs (`experience:12:bullet:3`, `project:2`) power traceability.

Tailoring pipeline: (1) deterministic TailoringEngine scores evidence against matched requirements and decides survival, order, projects surfaced, and skills ordering; (2) LLM rewrites the summary and selected bullets only within that scope, emitting per-bullet source_evidence_ids and a changes log; (3) deterministic ClaimVerification rejects any bullet whose technologies, numbers, employers, or titles are not traceable to source evidence.

State persistence: backend-persisted staging. The JobDescription row is the session root; each stepper step reads/writes server rows (JobDescription, JobAnalysis, match results, tailored resume, generated resume). Frontend holds only transient UI state and re-fetches on back-navigation. The stepper route carries the JobDescription id in the URL.

LLM abstraction: an LLMProvider Protocol with generate_structured support. Providers: Gemini (default), Groq, DeepSeek, selected by env var; a deterministic fixture provider for tests and demo mode. Structured output: Pydantic model → JSON schema → provider validation → Pydantic re-validation → one controlled retry → clean LLM_VALIDATION_FAILED.

API: routes per the build prompt (resumes CRUD, jobs/analyze, resumes/{id}/tailor, generated + pdf/latex/analysis endpoints), plus job submission/polling endpoints and GET /api/health. Routes are thin; logic lives in services. Errors are structured with codes: INVALID_RESUME, INVALID_JOB_DESCRIPTION, LLM_VALIDATION_FAILED, TAILORING_FAILED, LATEX_COMPILATION_FAILED, PDF_VALIDATION_FAILED, FILE_NOT_FOUND.

Document generation: single controlled article-based LaTeX template (geometry, lmodern, enumitem, titlesec, hyperref, glyphtounicode, pdfgentounicode). A dedicated LatexEscapeService escapes all user content. pdflatex runs in an isolated temp directory via subprocess argument arrays with timeout. Page count is accepted as an output and reported, never auto-fitted.

PDF validation: pdftotext extraction checks PDF validity, page count, presence of name/contact/headings/experience/education/skills, reading order, character integrity, and content preservation. Failures return structured PDF_VALIDATION_FAILED, never a valid PDF.

ATS Compatibility Analysis: reported as measured checks (required_keyword_coverage, preferred_keyword_coverage, evidence_coverage, pdf_text_extraction, single_column, standard_headings, critical_info_in_body, unexpected_tables, unexpected_graphics, page_count, warnings). Never presented as a pass/fail ATS score. Keyword coverage computed over high-priority required terms and preferred terms; evidence coverage over important requirements; unsupported requirements listed explicitly.

Database: entities Resume, ResumeVersion, JobDescription, JobAnalysis, GeneratedResume, ATSAnalysis, Job. UUIDs, timestamps, Alembic migrations. JSONB for structured resume data, job analysis, and evidence provenance.

Storage: StorageService protocol over local Docker volumes (/storage/uploads, /storage/latex, /storage/pdf), swappable for S3-compatible storage later.

Frontend: React + TypeScript + Vite + React Router + Tailwind CSS. Routes: /, /dashboard, /resume, /create, /create/job-analysis, /create/match, /create/review, /create/result, /history. Create flow is a stepper (MASTER CV, JOB, ANALYSIS, MATCH, GENERATE, REVIEW, ATS, EXPORT). PDF preview via native browser viewer in an iframe blob URL (zoom, pages, download).

Testing: pytest with Testcontainers-managed Postgres for integration tests; fakes/in-memory repos for unit tests; temp-dir StorageService. The fixture LLM provider makes the entire pipeline deterministic in CI.

## Testing Decisions

A good test asserts external behavior at a service or API boundary, never implementation details, and never needs an LLM key (fixture provider). The primary seam is the service layer with injected fake repositories and storage; the integration seam is the API against real Postgres (Testcontainers); the PDF seam is subprocess pdflatex/pdftotext against generated .tex.

- Resume: validation, CRUD, versioning (snapshot on tailor, master never mutated).
- Job analysis: requirement extraction, classification, normalization, importance.
- Matching: strong / partial / transferable / missing outcomes from catalog rules; synonym resolution; no FastAPI↔Flask equivalence.
- Tailoring: no hallucinated technologies, no invented metrics, source evidence preservation, schema validation, traceability of every bullet.
- LaTeX escaping: & % $ # _ { } plus URLs, Unicode, accented characters, long bullets.
- PDF: compilation, text extraction, expected headings, name/contact present, page count, corrupted/missing output.
- ClaimVerification: rejects untraceable claims, passes traceable ones.
- Acceptance: full flow (create master → analyze → match → tailor → latex → pdf → validate) via fixture provider.

## Out of Scope

Authentication, payments, subscriptions, teams, social login, email, mobile app, browser extensions, job scraping, automatic job applications, analytics dashboards, complex AI agents, multi-tenancy, Redis/job infrastructure, and any proprietary "ATS score". No deployment target beyond Docker Compose.

## Phase plan

Development order is fixed by the build prompt's Phase 1–8, tracked as GitHub issues in `yuc31gu1/ATS-CV-Maker`:

| Phase | Issue | Scope | Status |
| ----- | ----- | ----- | ------ |
| T1 | #2 | Foundation & connectivity (repo structure, Docker Compose, FastAPI, React, Postgres, Alembic, GET /api/health) | Closed |
| T2 | #3 | Master Resume (model, CRUD API, editor) | Closed |
| T3 | #4 | Job Analysis (background ANALYZE job, LLM abstraction, fixture provider) | Closed |
| T4 | #5 | Candidate Evidence Matching (rules + Skill Catalog, synchronous MATCH) | Open |
| T5 | #6 | Tailoring (TailoringEngine, LLM bullet rewrite, ClaimVerification) | Open |
| T6 | #7 | Document Generation (LaTeX renderer, escaping, PDF compilation) | Open |
| T7 | #8 | PDF Validation & ATS Analysis | Open |
| T8 | #9 | Product UX (stepper, PDF preview, history, dashboard, acceptance flow) | Open |

The glossary in `CONTEXT.md` governs vocabulary; ADRs 0001–0004 record the architectural commitments.