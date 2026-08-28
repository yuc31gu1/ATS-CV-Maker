from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from app.domain.analysis import Importance, RequirementCategory


class MatchStatus(str, Enum):
    """One axis of direct-evidence strength between a requirement and evidence."""

    STRONG_MATCH = "STRONG_MATCH"
    PARTIAL_MATCH = "PARTIAL_MATCH"
    TRANSFERABLE = "TRANSFERABLE"
    NO_EVIDENCE = "NO_EVIDENCE"


class EvidenceMatch(BaseModel):
    """A Job Requirement matched against Master Resume evidence (ADR-0002)."""

    requirement: str
    category: RequirementCategory
    importance: Importance
    status: MatchStatus
    matched_skill: str | None = None
    ambiguous: bool = False
    rationale: str = ""
    evidence_ids: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)


class MatchResult(BaseModel):
    """The persisted requirement–evidence matching result for one job."""

    job_description_id: str
    resume_id: str
    matches: list[EvidenceMatch] = Field(default_factory=list)
    created_at: datetime