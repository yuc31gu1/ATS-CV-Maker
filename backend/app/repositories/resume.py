import uuid
from typing import Protocol, runtime_checkable

from sqlalchemy.orm import sessionmaker

from app.db import SessionLocal
from app.domain.resume import Resume
from app.models import ResumeRow


@runtime_checkable
class ResumeRepository(Protocol):
    def create(self, resume: Resume) -> Resume: ...

    def get(self, resume_id: str) -> Resume | None: ...

    def list(self) -> list[Resume]: ...

    def update(self, resume_id: str, resume: Resume) -> Resume | None: ...


class InMemoryResumeRepository:
    """In-memory resume store for unit tests. Returns deep copies so callers
    can never mutate the canonical stored resume."""

    def __init__(self) -> None:
        self._resumes: dict[str, Resume] = {}

    def create(self, resume: Resume) -> Resume:
        stored = resume.model_copy(deep=True)
        self._resumes[stored.id] = stored
        return stored.model_copy(deep=True)

    def get(self, resume_id: str) -> Resume | None:
        stored = self._resumes.get(resume_id)
        return stored.model_copy(deep=True) if stored else None

    def list(self) -> list[Resume]:
        return [r.model_copy(deep=True) for r in self._resumes.values()]

    def update(self, resume_id: str, resume: Resume) -> Resume | None:
        if resume_id not in self._resumes:
            return None
        updated = resume.model_copy(deep=True)
        updated.id = resume_id
        self._resumes[resume_id] = updated
        return updated.model_copy(deep=True)


class SqlAlchemyResumeRepository:
    """Persists the Master Resume to Postgres: canonical content as JSONB with
    the id/schema_version lifted onto the row."""

    def __init__(self, session_factory: sessionmaker) -> None:
        self._session_factory = session_factory

    @staticmethod
    def _to_row(resume: Resume) -> ResumeRow:
        resume_id = resume.id or str(uuid.uuid4())
        return ResumeRow(
            id=resume_id,
            schema_version=resume.schema_version,
            data=resume.model_dump(exclude={"id"}),
        )

    @staticmethod
    def _from_row(row: ResumeRow) -> Resume:
        return Resume.model_validate({**row.data, "id": row.id})

    def create(self, resume: Resume) -> Resume:
        row = self._to_row(resume)
        with self._session_factory() as session:
            session.add(row)
            session.commit()
            session.refresh(row)
        return self._from_row(row)

    def get(self, resume_id: str) -> Resume | None:
        with self._session_factory() as session:
            row = session.get(ResumeRow, resume_id)
        return self._from_row(row) if row else None

    def list(self) -> list[Resume]:
        with self._session_factory() as session:
            rows = session.query(ResumeRow).order_by(ResumeRow.created_at).all()
        return [self._from_row(row) for row in rows]

    def update(self, resume_id: str, resume: Resume) -> Resume | None:
        with self._session_factory() as session:
            row = session.get(ResumeRow, resume_id)
            if row is None:
                return None
            row.schema_version = resume.schema_version
            row.data = resume.model_dump(exclude={"id"})
            session.commit()
            session.refresh(row)
            updated = self._from_row(row)
        return updated


def default_resume_repository() -> ResumeRepository:
    return SqlAlchemyResumeRepository(SessionLocal)