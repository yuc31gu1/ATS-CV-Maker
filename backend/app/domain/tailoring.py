from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from app.domain.resume import (
    Certification,
    Education,
    Experience,
    PersonalInformation,
    Project,
)


class TailorChangeKind(str, Enum):
    SUMMARY = "SUMMARY"
    BULLET = "BULLET"


class ChangeStatus(str, Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    EDITED = "EDITED"


class ChangeAction(str, Enum):
    accept = "accept"
    reject = "reject"
    edit = "edit"


class TailoredChange(BaseModel):
    """One engine-selected rewrite: original / tailored / reason (review row).

    A Tailored Resume is never silently changed: every change is surfaced for
    review with its original text, the tailored text, and the LLM's reason.
    """

    key: str
    kind: TailorChangeKind
    section: str
    original: str
    tailored: str
    reason: str = ""
    source_evidence_ids: list[str] = Field(default_factory=list)
    status: ChangeStatus = ChangeStatus.PENDING
    edited_text: str | None = None


class ReviewDecision(BaseModel):
    """A reviewer's decision on one change: accept, reject, or edit."""

    key: str
    action: ChangeAction
    text: str | None = None


class RewrittenBullet(BaseModel):
    """A single bullet rewrite produced by the LLM, scoped to one evidence id."""

    evidence_id: str
    text: str
    reason: str = ""
    source_evidence_ids: list[str] = Field(default_factory=list)


class LLMTailoredOutput(BaseModel):
    """Structured output the LLM must produce for the tailoring rewrite.

    The LLM rewrites wording only inside the engine-selected scope; it emits
    per-bullet source_evidence_ids so Claim Verification can reject any claim
    that is not traceable to source evidence.
    """

    summary: str | None = None
    summary_reason: str = ""
    summary_source_evidence_ids: list[str] = Field(default_factory=list)
    bullets: list[RewrittenBullet] = Field(default_factory=list)


class SelectedBullet(BaseModel):
    """Engine-selected bullet within LLM rewrite scope."""

    evidence_id: str
    original: str
    matched_requirements: list[str] = Field(default_factory=list)
    score: int = 0


class SelectedProject(BaseModel):
    """Engine-selected project that surfaces in the Tailored Resume."""

    index: int
    name: str
    matched_requirements: list[str] = Field(default_factory=list)


class TailoringScope(BaseModel):
    """Deterministic engine output: the exact evidence the LLM may rewrite.

    The engine decides which evidence survives, its order, which projects
    surface, and the skills ordering. The LLM never rewrites outside this
    scope (ADR-0001).
    """

    summary: str
    bullets: list[SelectedBullet] = Field(default_factory=list)
    projects: list[SelectedProject] = Field(default_factory=list)
    skills: dict[str, list[str]] = Field(default_factory=dict)


class TailoredResume(BaseModel):
    """The Tailored Resume for one job, pinned to an immutable ResumeVersion.

    Content is chosen and reworded from Master Resume evidence by the
    Tailoring Engine, before any rendering. It never mutates the Master
    Resume: it pins to the ResumeVersion snapshot captured when the job
    started (ADR-0004).
    """

    job_description_id: str
    resume_version_id: str
    resume_id: str
    personal_information: PersonalInformation
    summary: str
    skills: dict[str, list[str]] = Field(default_factory=dict)
    experience: list[Experience] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    certifications: list[Certification] = Field(default_factory=list)
    changes: list[TailoredChange] = Field(default_factory=list)
    created_at: datetime