from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from app.domain.analysis import JobRequirement


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