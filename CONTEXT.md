# ATS CV Maker — Domain Context

The product takes a canonical Master Resume and a Job Description, and produces a job-specific, ATS-optimized Tailored Resume as a validated PDF and LaTeX source. The domain model treats the resume as structured, evidence-traceable data; the deliverable is a machine-readable document, not a styled template.

## Language

**Resume**:
The structured representation of a person's career (personal info, summary, skills, experience, education, projects, certifications).
_Avoid_: CV (resume vs the deliverable); CV is product/UI copy only.

**Master Resume**:
The single canonical Resume the user edits. The source of truth for all evidence.
_Avoid_: master CV, base resume

**ResumeVersion**:
An immutable snapshot of the Master Resume captured when a tailoring job starts. Generated artifacts pin to a ResumeVersion, never to the live Master Resume, so history stays reproducible.
_Avoid_: revision, draft

**Tailored Resume**:
A Resume produced for one specific job: content chosen and reworded from Master Resume evidence by the Tailoring Engine, before any rendering.
_Avoid_: customized CV

**Generated Resume**:
The persisted delivery bundle for one job: Tailored Resume + Job Description reference + LaTeX source + compiled PDF + ATS Compatibility Analysis.
_Avoid_: output, result

**Job Description**:
Unstructured, untrusted user input describing a target role. Never interpolated into shell commands or LaTeX.
_Avoid_: JD (abbreviation acceptable in code), posting

**Job Requirement**:
A classified element extracted from a Job Description (required skill, preferred skill, responsibility, seniority signal, domain requirement, soft skill), each with an importance.
_Avoid_: keyword (reductive), requirement item

**Evidence**:
A traceable claim unit in the Master Resume (a bullet, a project, a skill entry) that can back a claim in a Tailored Resume. Identified by a deterministic Evidence ID (`experience:12:bullet:3`).
_Avoid_: fact, data point, source

**Match Status**:
One axis of direct-evidence strength between a Job Requirement and the candidate's evidence: `STRONG_MATCH` (direct + substantiated) · `PARTIAL_MATCH` (direct but shallow) · `TRANSFERABLE` (no direct evidence, adjacent exists) · `NO_EVIDENCE` (none). Assigned by rules, never by the LLM.
_Avoid_: score, match percentage

**Skill Catalog**:
The curated, checked-in vocabulary that resolves skill synonyms (`AWS` = `Amazon Web Services`) and marks distinct-but-adjacent technologies (`FastAPI` vs `Flask` — related, not synonyms). The controlled "semantic" layer for matching.
_Avoid_: keyword list, synonym map

**Tailoring Engine**:
The deterministic component that decides which evidence survives into a Tailored Resume, its order, and which JD terminology is supported. The LLM rewrites wording only inside the engine-selected scope. The engine never invents evidence.
_Avoid_: AI, generator

**Claim Verification**:
The deterministic gate that rejects any Tailored Resume bullet whose claims (technologies, numbers, employers) are not traceable to source evidence.
_Avoid_: quality check, linting

**ATS Compatibility Analysis**:
The measured, non-proprietary report of machine-readability checks (keyword coverage, PDF text extraction, single-column, standard headings, critical info in body, page count). Never presented as a pass/fail "ATS score".
_Avoid_: ATS score, ATS rating

**Job**:
A unit of background work with a type and status. Heavy LLM stages (`ANALYZE`, `TAILOR`) run as jobs; fast deterministic stages (`MATCH`, `GENERATE`) run synchronously.
_Avoid_: task, worker, pipeline run
