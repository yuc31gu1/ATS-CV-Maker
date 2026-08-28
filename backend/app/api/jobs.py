from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies import get_job_service
from app.schemas import JobError, JobOut, JobStatus
from app.services.jobs import JobService

router = APIRouter()


@router.get("/jobs", response_model=list[JobOut])
def list_jobs(
    job_service: Annotated[JobService, Depends(get_job_service)],
    type: str | None = None,
    job_description_id: str | None = None,
) -> list[JobOut]:
    """List jobs (newest first), optionally filtered by type and session root.

    Lets the stepper resume a background job (e.g. an ANALYZE already in
    flight) on back-navigation without re-submitting it (ADR-0003).
    """
    return [
        JobOut(
            id=job.id,
            type=job.type,
            status=JobStatus(job.status),
            result=job.result,
            error=(
                JobError(code=job.error_code, message=job.error_message)
                if job.error_code is not None
                else None
            ),
        )
        for job in job_service.list(
            job_type=type, job_description_id=job_description_id
        )
    ]


@router.get("/jobs/{job_id}", response_model=JobOut)
def get_job(
    job_id: str,
    job_service: Annotated[JobService, Depends(get_job_service)],
) -> JobOut:
    job = job_service.get(job_id)
    return JobOut(
        id=job.id,
        type=job.type,
        status=JobStatus(job.status),
        result=job.result,
        error=(
            JobError(code=job.error_code, message=job.error_message)
            if job.error_code is not None
            else None
        ),
    )