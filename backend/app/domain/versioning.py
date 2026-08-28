from datetime import datetime

from pydantic import BaseModel

from app.domain.resume import Resume


class ResumeVersion(BaseModel):
    """An immutable snapshot of the Master Resume (ADR-0004).

    Captured when a tailoring job starts. Generated artifacts (Tailored
    Resume, later the Generated Resume) pin to a ResumeVersion, never to the
    live Master Resume, so history stays reproducible even if the master
    changes later.
    """

    id: str
    resume_id: str
    data: Resume
    created_at: datetime