from collections.abc import Iterator
from pathlib import Path
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.config import settings
from app.db import SessionLocal
from app.llm.fixture import FixtureLLMProvider
from app.pdf.validator import PdfValidator
from app.repositories import mappers
from app.repositories.sqlalchemy import SqlAlchemyRepository
from app.services.analysis import AnalysisService
from app.services.ats import AtsAnalysisService
from app.services.dashboard import DashboardService
from app.services.generation import GenerationService
from app.services.jobs import JobService
from app.services.matching import MatchingService
from app.services.tailoring import TailoringService
from app.storage.local import LocalStorageService

_LLM_PROVIDER = FixtureLLMProvider()


def get_llm_provider() -> FixtureLLMProvider:
    if settings.llm_provider != "fixture":
        raise RuntimeError(f"LLM provider {settings.llm_provider!r} is not implemented yet")
    return _LLM_PROVIDER


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_job_service(db: Annotated[Session, Depends(get_db)]) -> JobService:
    from app.models import Job

    return JobService(
        SqlAlchemyRepository(db, Job, mappers.job_to_row, mappers.job_from_row)
    )


def get_analysis_service(
    db: Annotated[Session, Depends(get_db)],
    llm_provider: Annotated[FixtureLLMProvider, Depends(get_llm_provider)],
) -> AnalysisService:
    from app.models import JobAnalysis, JobDescription

    return AnalysisService(
        jd_repository=SqlAlchemyRepository(
            db,
            JobDescription,
            mappers.job_description_to_row,
            mappers.job_description_from_row,
        ),
        analysis_repository=SqlAlchemyRepository(
            db, JobAnalysis, mappers.job_analysis_to_row, mappers.job_analysis_from_row
        ),
        llm_provider=llm_provider,
    )


def get_matching_service(db: Annotated[Session, Depends(get_db)]) -> MatchingService:
    from app.models import JobAnalysis, MatchResultRow

    return MatchingService(
        analysis_repository=SqlAlchemyRepository(
            db, JobAnalysis, mappers.job_analysis_to_row, mappers.job_analysis_from_row
        ),
        match_repository=SqlAlchemyRepository(
            db, MatchResultRow, mappers.match_result_to_row, mappers.match_result_from_row
        ),
    )


def get_tailoring_service(
    db: Annotated[Session, Depends(get_db)],
    llm_provider: Annotated[FixtureLLMProvider, Depends(get_llm_provider)],
) -> TailoringService:
    from app.models import (
        JobAnalysis,
        MatchResultRow,
        ResumeVersionRow,
        TailoredResumeRow,
    )
    from app.repositories.resume import SqlAlchemyResumeRepository

    return TailoringService(
        version_repository=SqlAlchemyRepository(
            db,
            ResumeVersionRow,
            mappers.resume_version_to_row,
            mappers.resume_version_from_row,
        ),
        tailored_repository=SqlAlchemyRepository(
            db,
            TailoredResumeRow,
            mappers.tailored_resume_to_row,
            mappers.tailored_resume_from_row,
        ),
        resume_repository=SqlAlchemyResumeRepository(SessionLocal),
        analysis_repository=SqlAlchemyRepository(
            db, JobAnalysis, mappers.job_analysis_to_row, mappers.job_analysis_from_row
        ),
        match_repository=SqlAlchemyRepository(
            db, MatchResultRow, mappers.match_result_to_row, mappers.match_result_from_row
        ),
        llm_provider=llm_provider,
    )


def get_storage_service() -> LocalStorageService:
    return LocalStorageService(Path(settings.storage_root))


def get_pdf_validator() -> PdfValidator:
    return PdfValidator()


def get_ats_analysis_service(
    db: Annotated[Session, Depends(get_db)],
) -> AtsAnalysisService:
    from app.models import JobAnalysis, MatchResultRow

    return AtsAnalysisService(
        analysis_repository=SqlAlchemyRepository(
            db, JobAnalysis, mappers.job_analysis_to_row, mappers.job_analysis_from_row
        ),
        match_repository=SqlAlchemyRepository(
            db, MatchResultRow, mappers.match_result_to_row, mappers.match_result_from_row
        ),
    )


def get_generation_service(
    db: Annotated[Session, Depends(get_db)],
    storage: Annotated[LocalStorageService, Depends(get_storage_service)],
    validator: Annotated[PdfValidator, Depends(get_pdf_validator)],
    ats: Annotated[AtsAnalysisService, Depends(get_ats_analysis_service)],
) -> GenerationService:
    from app.models import GeneratedResumeRow, TailoredResumeRow

    return GenerationService(
        tailored_repository=SqlAlchemyRepository(
            db,
            TailoredResumeRow,
            mappers.tailored_resume_to_row,
            mappers.tailored_resume_from_row,
        ),
        generated_repository=SqlAlchemyRepository(
            db,
            GeneratedResumeRow,
            mappers.generated_resume_to_row,
            mappers.generated_resume_from_row,
        ),
        storage=storage,
        validator=validator,
        ats=ats,
    )


def get_dashboard_service(
    db: Annotated[Session, Depends(get_db)],
) -> DashboardService:
    from app.models import (
        GeneratedResumeRow,
        JobAnalysis,
        JobDescription,
        TailoredResumeRow,
    )
    from app.repositories.resume import SqlAlchemyResumeRepository

    return DashboardService(
        resume_repository=SqlAlchemyResumeRepository(SessionLocal),
        jd_repository=SqlAlchemyRepository(
            db,
            JobDescription,
            mappers.job_description_to_row,
            mappers.job_description_from_row,
        ),
        analysis_repository=SqlAlchemyRepository(
            db, JobAnalysis, mappers.job_analysis_to_row, mappers.job_analysis_from_row
        ),
        tailored_repository=SqlAlchemyRepository(
            db,
            TailoredResumeRow,
            mappers.tailored_resume_to_row,
            mappers.tailored_resume_from_row,
        ),
        generated_repository=SqlAlchemyRepository(
            db,
            GeneratedResumeRow,
            mappers.generated_resume_to_row,
            mappers.generated_resume_from_row,
        ),
    )
