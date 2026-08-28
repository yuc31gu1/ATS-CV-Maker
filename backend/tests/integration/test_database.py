import shutil
from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, text
from testcontainers.postgres import PostgresContainer

from alembic import command
from app.domain.resume import Experience, PersonalInformation, Resume
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
def test_migrations_apply_to_postgres() -> None:
    with PostgresContainer("postgres:16-alpine") as postgres:
        url = _psycopg_url(postgres)
        command.upgrade(_alembic_config(url), "head")

        engine = create_engine(url)
        with engine.connect() as conn:
            version = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
            tables = conn.execute(
                text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
            ).scalars()
        assert version == "0002"
        assert "resumes" in set(tables)


@pytest.mark.skipif(shutil.which("docker") is None, reason="Docker unavailable")
def test_sqlalchemy_resume_repository_roundtrip() -> None:
    from sqlalchemy.orm import sessionmaker

    from app.repositories.resume import SqlAlchemyResumeRepository

    with PostgresContainer("postgres:16-alpine") as postgres:
        url = _psycopg_url(postgres)
        command.upgrade(_alembic_config(url), "head")

        repo = SqlAlchemyResumeRepository(sessionmaker(bind=create_engine(url)))
        created = repo.create(_resume())
        fetched = repo.get(created.id)
        assert fetched == created
        assert fetched.personal_information.full_name == "Ada Lovelace"

        listed = repo.list()
        assert [r.id for r in listed] == [created.id]

        updated = repo.update(
            created.id,
            Resume.model_validate({**created.model_dump(exclude={"id"}), "summary": "Updated"}),
        )
        assert updated.summary == "Updated"
        assert repo.get(created.id).summary == "Updated"


def _resume() -> Resume:
    return Resume(
        personal_information=PersonalInformation(full_name="Ada Lovelace"),
        summary="Deterministic document pipelines.",
        experience=[Experience(company="Analytical Engines Ltd", title="Engineer", start_date="2021-03")],
    )


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