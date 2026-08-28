import pytest

from app.domain.jobs import (
    JOB_STATUS_FAILED,
    JOB_STATUS_PENDING,
    JOB_STATUS_RUNNING,
    JOB_STATUS_SUCCEEDED,
    JOB_TYPE_ANALYZE,
)
from app.errors import NotFoundError
from app.repositories.in_memory import InMemoryRepository
from app.services.jobs import JobService


def make_service() -> JobService:
    return JobService(InMemoryRepository())


def test_job_service_runs_lifecycle_transitions():
    service = make_service()
    job = service.create(JOB_TYPE_ANALYZE, {"job_description_id": "jd-1"})
    assert job.status == JOB_STATUS_PENDING

    observed = []

    def handler(job_id: str) -> dict:
        observed.append(service.get(job_id).status)
        return {"ok": True}

    result = service.execute(job.id, handler)

    finished = service.get(job.id)
    assert finished.status == JOB_STATUS_SUCCEEDED
    assert finished.result == result == {"ok": True}
    assert observed == [JOB_STATUS_RUNNING]


def test_job_service_marks_failed_with_app_error_code():
    service = make_service()
    job = service.create(JOB_TYPE_ANALYZE, {})

    def handler(job_id: str) -> dict:
        raise NotFoundError("missing")

    service.execute(job.id, handler)

    failed = service.get(job.id)
    assert failed.status == JOB_STATUS_FAILED
    assert failed.error_code == "NOT_FOUND"
    assert failed.result is None


def test_job_service_masks_unexpected_errors():
    service = make_service()
    job = service.create(JOB_TYPE_ANALYZE, {})

    def handler(job_id: str) -> dict:
        raise RuntimeError("secret internal detail")

    service.execute(job.id, handler)

    failed = service.get(job.id)
    assert failed.status == JOB_STATUS_FAILED
    assert failed.error_code == "INTERNAL_ERROR"
    assert "secret internal detail" not in failed.error_message


def test_job_service_get_missing_raises_not_found():
    service = make_service()
    with pytest.raises(NotFoundError):
        service.get("nope")