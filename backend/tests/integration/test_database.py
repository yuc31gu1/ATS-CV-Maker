import shutil
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from testcontainers.postgres import PostgresContainer

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
        assert version == "0001"


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