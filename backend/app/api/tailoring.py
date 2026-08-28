from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends

from app.dependencies import get_job_service, get_tailoring_service
from app.domain.jobs import JOB_TYPE_TAILOR
from app.domain.tailoring import TailoredResume
from app.errors import NotFoundError
from app.schemas import (
    RegenerateIn,
    ReviewDecisionsIn,
    TailorIn,
    TailorSubmitResponse,
)
from app.services.jobs import JobService
from app.services.tailoring import TailoringService

router = APIRouter()

TailoringServiceDependency = Annotated[TailoringService, Depends(get_tailoring_service)]


def _run_tailor(
    job_service: JobService, tailoring_service: TailoringService, job_id: str
) -> None:
    def handle(job_id: str) -> dict:
        job = job_service.get(job_id)
        return tailoring_service.run(job.payload)

    job_service.execute(job_id, handle)


def _submit_tailor_job(
    job_service: JobService,
    tailoring_service: TailoringService,
    background_tasks: BackgroundTasks,
    payload: dict,
    job_description_id: str,
    resume_id: str | None,
) -> TailorSubmitResponse:
    job = job_service.create(JOB_TYPE_TAILOR, payload)
    background_tasks.add_task(_run_tailor, job_service, tailoring_service, job.id)
    return TailorSubmitResponse(
        job_id=job.id,
        job_description_id=job_description_id,
        resume_id=resume_id or "",
        status=job.status,
    )


@router.post(
    "/resumes/{resume_id}/tailor",
    response_model=TailorSubmitResponse,
    status_code=201,
)
def create_tailor_job(
    resume_id: str,
    payload: TailorIn,
    background_tasks: BackgroundTasks,
    job_service: Annotated[JobService, Depends(get_job_service)],
    tailoring_service: TailoringServiceDependency,
) -> TailorSubmitResponse:
    """Start a TAILOR background job for one job and the given Master Resume."""
    return _submit_tailor_job(
        job_service,
        tailoring_service,
        background_tasks,
        {"job_description_id": payload.job_description_id, "resume_id": resume_id},
        payload.job_description_id,
        resume_id,
    )


@router.get(
    "/job-descriptions/{job_description_id}/tailored",
    response_model=TailoredResume,
)
def get_tailored(
    job_description_id: str,
    tailoring_service: TailoringServiceDependency,
) -> TailoredResume:
    """Fetch the staged Tailored Resume for the review step (never the master)."""
    tailored = tailoring_service.get(job_description_id)
    if tailored is None:
        raise NotFoundError(
            "tailored resume not found",
            details={"job_description_id": job_description_id},
        )
    return tailored


@router.post(
    "/job-descriptions/{job_description_id}/tailored/decisions",
    response_model=TailoredResume,
)
def apply_review_decisions(
    job_description_id: str,
    payload: ReviewDecisionsIn,
    tailoring_service: TailoringServiceDependency,
) -> TailoredResume:
    """Record accept / reject / edit decisions per change on the staged resume."""
    return tailoring_service.apply_decisions(job_description_id, payload.decisions)


@router.post(
    "/job-descriptions/{job_description_id}/tailored/regenerate",
    response_model=TailorSubmitResponse,
    status_code=201,
)
def regenerate_change(
    job_description_id: str,
    payload: RegenerateIn,
    background_tasks: BackgroundTasks,
    job_service: Annotated[JobService, Depends(get_job_service)],
    tailoring_service: TailoringServiceDependency,
) -> TailorSubmitResponse:
    """Re-run the LLM for one change as a TAILOR job (ADR-0003)."""
    tailored = tailoring_service.get(job_description_id)
    resume_id = tailored.resume_id if tailored is not None else None
    return _submit_tailor_job(
        job_service,
        tailoring_service,
        background_tasks,
        {
            "job_description_id": job_description_id,
            "action": "regenerate",
            "change_key": payload.change_key,
        },
        job_description_id,
        resume_id,
    )