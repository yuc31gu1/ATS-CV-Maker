from typing import Annotated

from fastapi import APIRouter, Depends, Response

from app.dependencies import get_generation_service
from app.domain.ats import ATSAnalysis
from app.domain.generated import GeneratedResume
from app.errors import NotFoundError
from app.services.generation import GenerationService

router = APIRouter()

GenerationServiceDependency = Annotated[
    GenerationService, Depends(get_generation_service)
]


def _require_generated(
    generation_service: GenerationService, job_description_id: str
) -> GeneratedResume:
    generated = generation_service.get(job_description_id)
    if generated is None:
        raise NotFoundError(
            "generated resume not found",
            details={"job_description_id": job_description_id},
        )
    return generated


@router.post(
    "/job-descriptions/{job_description_id}/generated",
    response_model=GeneratedResume,
    status_code=201,
)
def generate_document(
    job_description_id: str,
    generation_service: GenerationServiceDependency,
) -> GeneratedResume:
    """Render and compile the Tailored Resume synchronously (ADR-0003)."""
    return generation_service.generate(job_description_id)


@router.get(
    "/job-descriptions/{job_description_id}/generated",
    response_model=GeneratedResume,
)
def get_generated(
    job_description_id: str,
    generation_service: GenerationServiceDependency,
) -> GeneratedResume:
    """Fetch the Generated Resume metadata for the job description."""
    return _require_generated(generation_service, job_description_id)


@router.get(
    "/job-descriptions/{job_description_id}/generated/analysis",
    response_model=ATSAnalysis,
)
def get_generated_analysis(
    job_description_id: str,
    generation_service: GenerationServiceDependency,
) -> ATSAnalysis:
    """Fetch the measured ATS Compatibility Analysis for the job description."""
    generated = _require_generated(generation_service, job_description_id)
    if generated.ats_analysis is None:
        raise NotFoundError(
            "ats analysis not found",
            details={"job_description_id": job_description_id},
        )
    return generated.ats_analysis


@router.get(
    "/job-descriptions/{job_description_id}/generated/pdf",
    response_class=Response,
)
def get_generated_pdf(
    job_description_id: str,
    generation_service: GenerationServiceDependency,
) -> Response:
    """Download the compiled PDF for the job description."""
    generated = _require_generated(generation_service, job_description_id)
    return Response(
        content=generation_service.pdf_bytes(generated),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{job_description_id}.pdf"'
        },
    )


@router.get(
    "/job-descriptions/{job_description_id}/generated/latex",
    response_class=Response,
)
def get_generated_latex(
    job_description_id: str,
    generation_service: GenerationServiceDependency,
) -> Response:
    """Download the LaTeX source for the job description."""
    generated = _require_generated(generation_service, job_description_id)
    return Response(
        content=generation_service.latex_bytes(generated),
        media_type="application/x-tex",
        headers={
            "Content-Disposition": f'attachment; filename="{job_description_id}.tex"'
        },
    )