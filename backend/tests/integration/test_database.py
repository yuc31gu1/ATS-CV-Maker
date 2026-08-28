import shutil
from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, text
from testcontainers.postgres import PostgresContainer

from alembic import command
from app.main import app
from app.services.health import HealthService, get_health_service

pytestmark = pytest.mark.integration

BACKEND_DIR = Path(__file__).resolve().parents[2]


def _alembic_config(database_url: str) -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", database_url)
    return cfg


def _psycopg_url(postgres: PostgresContainer) -> str:
    return postgres.get_connection_url().replace(
        "postgresql+psycopg2://", "postgresql+psycopg://"
    )


@pytest.mark.skipif(shutil.which("docker") is None, reason="Docker unavailable")
def test_initial_migration_applies_to_postgres() -> None:
    with PostgresContainer("postgres:16-alpine") as postgres:
        url = _psycopg_url(postgres)
        command.upgrade(_alembic_config(url), "head")

        engine = create_engine(url)
        with engine.connect() as conn:
            version = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
        assert version == "0002"


@pytest.mark.skipif(shutil.which("docker") is None, reason="Docker unavailable")
def test_health_reports_database_ok() -> None:
    from fastapi.testclient import TestClient

    with PostgresContainer("postgres:16-alpine") as postgres:
        url = _psycopg_url(postgres)
        command.upgrade(_alembic_config(url), "head")

        app.dependency_overrides[get_health_service] = lambda: HealthService(
            create_engine(url)
        )
        with TestClient(app) as client:
            body = client.get("/api/health").json()
        app.dependency_overrides.clear()

    assert body["database"]["status"] == "ok"


@pytest.mark.skipif(shutil.which("docker") is None, reason="Docker unavailable")
def test_job_description_analysis_and_job_persist() -> None:
    from sqlalchemy.orm import Session

    from app.llm.fixture import FixtureLLMProvider
    from app.models import Job, JobAnalysis, JobDescription
    from app.repositories.sqlalchemy import SqlAlchemyRepository
    from app.services.analysis import AnalysisService
    from app.services.jobs import JobService

    with PostgresContainer("postgres:16-alpine") as postgres:
        url = _psycopg_url(postgres)
        command.upgrade(_alembic_config(url), "head")

        engine = create_engine(url)
        session = Session(engine)
        jd_service = AnalysisService(
            jd_repository=SqlAlchemyRepository(session, JobDescription),
            analysis_repository=SqlAlchemyRepository(session, JobAnalysis),
            llm_provider=FixtureLLMProvider(),
        )
        job_service = JobService(SqlAlchemyRepository(session, Job))

        job_description = jd_service.create_job_description(
            company="Acme", role=None, location=None, jd_text="Role: Engineer\n- Must have Python\n"
        )
        analysis = jd_service.analyze_job(job_description.id)
        job = job_service.create("ANALYZE", {"job_description_id": job_description.id})

        session.commit()

        loaded_jd = session.get(JobDescription, job_description.id)
        loaded_analysis = session.get(JobAnalysis, job_description.id)
        loaded_job = session.get(Job, job.id)

        assert loaded_jd is not None
        assert loaded_analysis is not None
        assert loaded_analysis.role == analysis.role
        assert loaded_analysis.requirements[0]["requirement"] == "Must have Python"
        assert loaded_job is not None
        assert loaded_job.status == "PENDING"