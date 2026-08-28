from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.config import settings
from app.db import SessionLocal
from app.llm.fixture import FixtureLLMProvider
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

    return JobService(SqlAlchemyRepository(db, Job))


def get_analysis_service(
    db: Annotated[Session, Depends(get_db)],
    llm_provider: Annotated[FixtureLLMProvider, Depends(get_llm_provider)],
) -> AnalysisService:
    from app.models import JobAnalysis, JobDescription

    return AnalysisService(
        jd_repository=SqlAlchemyRepository(db, JobDescription),
        analysis_repository=SqlAlchemyRepository(db, JobAnalysis),
        llm_provider=llm_provider,
    )


def get_matching_service(db: Annotated[Session, Depends(get_db)]) -> MatchingService:
    from app.models import JobAnalysis, MatchResultRow

    return MatchingService(
        analysis_repository=SqlAlchemyRepository(db, JobAnalysis),
        match_repository=SqlAlchemyRepository(db, MatchResultRow),
    )