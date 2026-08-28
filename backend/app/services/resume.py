import uuid
from typing import Any

from pydantic import ValidationError

from app.domain.resume import Resume
from app.errors import InvalidResumeError, NotFoundError
from app.repositories.resume import ResumeRepository, default_resume_repository


class ResumeService:
    """Application service for the canonical Master Resume.

    Validates inbound data as an INVALID_RESUME error, assigns ids, and treats
    the stored resume as immutable: repository reads return copies so no caller
    (tailoring, generation) can ever mutate the master.
    """

    def __init__(self, repository: ResumeRepository) -> None:
        self._repository = repository

    def create(self, payload: dict[str, Any]) -> Resume:
        resume = self._validate(payload)
        resume.id = str(uuid.uuid4())
        return self._repository.create(resume)

    def get(self, resume_id: str) -> Resume:
        resume = self._repository.get(resume_id)
        if resume is None:
            raise NotFoundError("resume not found", details={"id": resume_id})
        return resume

    def list(self) -> list[Resume]:
        return self._repository.list()

    def update(self, resume_id: str, payload: dict[str, Any]) -> Resume:
        resume = self._validate(payload)
        resume.id = resume_id
        updated = self._repository.update(resume_id, resume)
        if updated is None:
            raise NotFoundError("resume not found", details={"id": resume_id})
        return updated

    @staticmethod
    def _validate(payload: dict[str, Any]) -> Resume:
        try:
            return Resume.model_validate(payload)
        except ValidationError as exc:
            raise InvalidResumeError(
                "invalid resume",
                details={"errors": exc.errors(include_url=False, include_context=False)},
            ) from exc


def get_resume_service() -> ResumeService:
    return ResumeService(default_resume_repository())