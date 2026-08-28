"""Alembic config plumbing — the URL a caller provides must win over settings.

The Testcontainers-backed integration tests build an Alembic ``Config`` that
points at an ephemeral Postgres and call ``command.upgrade``. ``alembic/env.py``
must honour that URL rather than silently replacing it with the app's
``settings.database_url``; otherwise migrations run against the wrong database.
"""

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config

from app import config as app_config

BACKEND_DIR = Path(__file__).resolve().parents[1]


def _alembic_config(database_url: str) -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", database_url)
    return cfg


def test_alembic_env_honours_caller_provided_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    """A config-provided URL is used even when settings point somewhere else.

    Regression: env.py used to unconditionally overwrite the config URL with
    ``settings.database_url``, so migrations always targeted the configured
    database instead of the ephemeral one the caller supplied.
    """
    monkeypatch.setattr(
        app_config.settings,
        "database_url",
        "postgresql+psycopg://bogus:bogus@127.0.0.1:9999/bogus",
    )
    cfg = _alembic_config("postgresql+psycopg://ats:ats@127.0.0.1:1/ats")

    with pytest.raises(Exception) as excinfo:
        command.upgrade(cfg, "head")

    assert "port 1" in str(excinfo.value)