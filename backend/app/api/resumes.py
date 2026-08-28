from typing import Annotated, Any

from fastapi import APIRouter, Depends

from app.domain.resume import Resume
from app.services.resume import ResumeService, get_resume_service

router = APIRouter(prefix="/resumes", tags=["resumes"])

ResumeServiceDependency = Annotated[ResumeService, Depends(get_resume_service)]


@router.post("", response_model=Resume, status_code=201)
def create_resume(
    payload: dict[str, Any],
    service: ResumeServiceDependency,
) -> Resume:
    return service.create(payload)


@router.get("", response_model=list[Resume])
def list_resumes(service: ResumeServiceDependency) -> list[Resume]:
    return service.list()


@router.get("/{resume_id}", response_model=Resume)
def get_resume(resume_id: str, service: ResumeServiceDependency) -> Resume:
    return service.get(resume_id)


@router.put("/{resume_id}", response_model=Resume)
def update_resume(
    resume_id: str,
    payload: dict[str, Any],
    service: ResumeServiceDependency,
) -> Resume:
    return service.update(resume_id, payload)