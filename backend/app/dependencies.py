from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.config import settings
from app.db import SessionLocal
from app.llm.fixture import FixtureLLMProvider
from app.repositories import mappers
from app.repositories.sqlalchemy import SqlAlchemyRepository
from app.services.analysis import AnalysisService
from app.services.jobs import JobService
from app.services.matching import MatchingService

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
