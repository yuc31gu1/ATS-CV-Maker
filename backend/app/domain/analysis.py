from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class RequirementCategory(str, Enum):
    REQUIRED = "REQUIRED"
    PREFERRED = "PREFERRED"
    RESPONSIBILITY = "RESPONSIBILITY"
    SENIORITY = "SENIORITY"
    DOMAIN = "DOMAIN"
    SOFT_SKILL = "SOFT_SKILL"


class Importance(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class JobRequirement(BaseModel):
    requirement: str
    category: RequirementCategory
    importance: Importance
    context: str


class LLMJobAnalysis(BaseModel):
    """Structured output the LLM must produce for a Job Description."""

    role: str
    seniority: str | None = None
    requirements: list[JobRequirement] = Field(default_factory=list)


class JobDescription(BaseModel):
    id: str
    company: str | None = None
    role: str | None = None
    location: str | None = None
    jd_text: str
    created_at: datetime


class JobAnalysis(BaseModel):
    id: str
    job_description_id: str
    role: str
    seniority: str | None = None
    requirements: list[JobRequirement] = Field(default_factory=list)
    created_at: datetime