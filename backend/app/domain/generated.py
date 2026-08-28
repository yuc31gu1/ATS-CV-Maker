from datetime import datetime

from pydantic import BaseModel

from app.domain.ats import ATSAnalysis


class GeneratedResume(BaseModel):
    """The persisted delivery bundle for one job (T6/T7).

    The Tailored Resume content, rendered as deterministic LaTeX and compiled
    to PDF. Pins to the immutable ResumeVersion snapshot (ADR-0004), never to
    the live Master Resume. The LaTeX source and compiled PDF live in the
    StorageService under ``latex_key`` / ``pdf_key``. The PDF passed the
    validation gate (T7); ``ats_analysis`` holds the measured ATS
    Compatibility Analysis.
    """

    job_description_id: str
    resume_version_id: str
    resume_id: str
    latex_key: str
    pdf_key: str
    created_at: datetime
    ats_analysis: ATSAnalysis | None = None