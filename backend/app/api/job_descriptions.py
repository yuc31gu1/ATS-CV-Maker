from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends

from app.dependencies import get_analysis_service, get_job_service
from app.domain.jobs import JOB_TYPE_ANALYZE
from app.errors import NotFoundError
from app.schemas import (
    JobAnalysisOut,
    JobDescriptionIn,
    JobDescriptionOut,
    JobDescriptionSubmitResponse,
)
from app.services.analysis import AnalysisService
from app.services.jobs import JobService

router = APIRouter()


def _run_analyze(
    job_service: JobService, analysis_service: AnalysisService, job_id: str
) -> None:
    def handle(job_id: str) -> dict:
        job = job_service.get(job_id)
        job_description_id = job.payload["job_description_id"]
        return analysis_service.analyze_job(job_description_id).model_dump(mode="json")

    job_service.execute(job_id, handle)


@router.post(
    "/job-descriptions",
    response_model=JobDescriptionSubmitResponse,
    status_code=201,
)
def create_job_description(
    payload: JobDescriptionIn,
    background_tasks: BackgroundTasks,
    job_service: Annotated[JobService, Depends(get_job_service)],
    analysis_service: Annotated[AnalysisService, Depends(get_analysis_service)],
) -> JobDescriptionSubmitResponse:
    job_description = analysis_service.create_job_description(
        company=payload.company,
        role=payload.role,
        location=payload.location,
        jd_text=payload.jd_text,
    )
    job = job_service.create(JOB_TYPE_ANALYZE, {"job_description_id": job_description.id})
    background_tasks.add_task(_run_analyze, job_service, analysis_service, job.id)
    return JobDescriptionSubmitResponse(
        job_description_id=job_description.id, job_id=job.id, status=job.status
    )


@router.get("/job-descriptions/{job_description_id}", response_model=JobDescriptionOut)
def get_job_description(
    job_description_id: str,
    analysis_service: Annotated[AnalysisService, Depends(get_analysis_service)],
) -> JobDescriptionOut:
    job_description = analysis_service.get_job_description(job_description_id)
    return JobDescriptionOut(**job_description.model_dump())


@router.get("/job-descriptions/{job_description_id}/analysis", response_model=JobAnalysisOut)
def get_job_analysis(
    job_description_id: str,
    analysis_service: Annotated[AnalysisService, Depends(get_analysis_service)],
) -> JobAnalysisOut:
    analysis = analysis_service.get_analysis(job_description_id)
    if analysis is None:
        raise NotFoundError(
            "job analysis not found", details={"job_description_id": job_description_id}
        )
    return JobAnalysisOut(
        job_description_id=analysis.job_description_id,
        role=analysis.role,
        seniority=analysis.seniority,
        requirements=analysis.requirements,
    )