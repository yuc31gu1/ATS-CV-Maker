from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from app.domain.analysis import Importance, JobRequirement, RequirementCategory
from app.domain.matching import MatchStatus
from app.domain.tailoring import ReviewDecision


class DatabaseStatus(str, Enum):
    ok = "ok"
    unavailable = "unavailable"


class HealthDatabase(BaseModel):
    status: DatabaseStatus


class HealthResponse(BaseModel):
    status: str
    service: str
    database: HealthDatabase


class JobDescriptionIn(BaseModel):
    company: str | None = Field(default=None, max_length=255)
    role: str | None = Field(default=None, max_length=255)
    location: str | None = Field(default=None, max_length=255)
    jd_text: str = Field(min_length=1, max_length=50_000)


class JobDescriptionOut(BaseModel):
    id: str
    company: str | None = None
    role: str | None = None
    location: str | None = None
    jd_text: str
    created_at: datetime


class JobDescriptionSubmitResponse(BaseModel):
    job_description_id: str
    job_id: str
    status: str


class JobStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class JobError(BaseModel):
    code: str
    message: str


class JobOut(BaseModel):
    id: str
    type: str
    status: JobStatus
    result: dict | None = None
    error: JobError | None = None


class JobAnalysisOut(BaseModel):
    job_description_id: str
    role: str
    seniority: str | None = None
    requirements: list[JobRequirement] = Field(default_factory=list)


class EvidenceMatchOut(BaseModel):
    requirement: str
    category: RequirementCategory
    importance: Importance
    status: MatchStatus
    matched_skill: str | None = None
    ambiguous: bool = False
    rationale: str = ""
    evidence_ids: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)


class MatchOut(BaseModel):
    job_description_id: str
    resume_id: str
    matches: list[EvidenceMatchOut] = Field(default_factory=list)
    created_at: datetime


class TailorIn(BaseModel):
    job_description_id: str


class TailorSubmitResponse(BaseModel):
    job_id: str
    job_description_id: str
    resume_id: str
    status: str


class RegenerateIn(BaseModel):
    change_key: str


class ReviewDecisionsIn(BaseModel):
    decisions: list[ReviewDecision] = Field(default_factory=list)