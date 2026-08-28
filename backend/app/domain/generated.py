from datetime import datetime

from pydantic import BaseModel


class GeneratedResume(BaseModel):
    """The persisted delivery bundle for one job (T6).

    The Tailored Resume content, rendered as deterministic LaTeX and compiled
    to PDF. Pins to the immutable ResumeVersion snapshot (ADR-0004), never to
    the live Master Resume. The LaTeX source and compiled PDF live in the
    StorageService under ``latex_key`` / ``pdf_key``.
    """

    job_description_id: str
    resume_version_id: str
    resume_id: str
    latex_key: str
    pdf_key: str
    created_at: datetime