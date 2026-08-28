from datetime import datetime

from pydantic import BaseModel, Field

from app.domain.resume import Resume


class ApplicationSummary(BaseModel):
    """One stepper session (a Job Description root) plus its reached stages.

    Drives the /history list and the dashboard's recent applications: which
    stages (analysis, tailoring, generation) have been reached for the job,
    so the UI can reopen a generated CV or continue an in-progress one.
    """

    job_description_id: str
    company: str | None = None
    role: str | None = None
    location: str | None = None
    created_at: datetime
    has_analysis: bool = False
    has_tailored: bool = False
    has_generated: bool = False


class DashboardSummary(BaseModel):
    """The dashboard read model: master resume, counts, recent applications."""

    master_resume: Resume | None = None
    tailored_cv_count: int = 0
    analyzed_jobs_count: int = 0
    recent_applications: list[ApplicationSummary] = Field(default_factory=list)