from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies import get_job_service
from app.schemas import JobError, JobOut, JobStatus
from app.services.jobs import JobService

router = APIRouter()


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