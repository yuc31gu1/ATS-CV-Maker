from datetime import UTC, datetime
from uuid import uuid4

from app.domain.jobs import (
    JOB_STATUS_FAILED,
    JOB_STATUS_PENDING,
    JOB_STATUS_RUNNING,
    JOB_STATUS_SUCCEEDED,
    Job,
)
from app.errors import AppError, NotFoundError
from app.repositories.base import EntityRepository


def utcnow() -> datetime:
    return datetime.now(UTC)


class JobService:
    """Tracks typed background jobs against a repository (ADR-0003)."""

    def __init__(self, job_repository: EntityRepository[Job]) -> None:
        self._jobs = job_repository

    def create(self, job_type: str, payload: dict) -> Job:
        now = utcnow()
        job = Job(
            id=str(uuid4()),
            type=job_type,
            status=JOB_STATUS_PENDING,
            payload=payload,
            created_at=now,
            updated_at=now,
        )
        return self._jobs.add(job.id, job)

    def get(self, job_id: str) -> Job:
        job = self._jobs.get(job_id)
        if job is None:
            raise NotFoundError("job not found", details={"id": job_id})
        return job

    def execute(self, job_id: str, handler) -> dict | None:
        """Run the in-process worker: PENDING -> RUNNING -> SUCCEEDED/FAILED."""
        self.mark_running(job_id)
        try:
            result = handler(job_id)
            self.succeed(job_id, result)
            return result
        except AppError as exc:
            self.fail(job_id, code=exc.code, message=exc.message)
        except Exception:
            self.fail(job_id, code="INTERNAL_ERROR", message="Job failed")
        return None

    def mark_running(self, job_id: str) -> Job:
        return self._transition(job_id, JOB_STATUS_RUNNING)

    def succeed(self, job_id: str, result: dict | None) -> Job:
        job = self.get(job_id)
        job.status = JOB_STATUS_SUCCEEDED
        job.result = result
        job.error_code = None
        job.error_message = None
        job.updated_at = utcnow()
        return self._jobs.add(job_id, job)

    def fail(self, job_id: str, *, code: str, message: str) -> Job:
        job = self.get(job_id)
        job.status = JOB_STATUS_FAILED
        job.error_code = code
        job.error_message = message
        job.updated_at = utcnow()
        return self._jobs.add(job_id, job)

    def _transition(self, job_id: str, status: str) -> Job:
        job = self.get(job_id)
        job.status = status
        job.updated_at = utcnow()
        return self._jobs.add(job_id, job)