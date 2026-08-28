import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.domain.resume import CURRENT_SCHEMA_VERSION


def _utcnow() -> datetime:
    return datetime.now(UTC)


class ResumeRow(Base):
    """Persisted Master Resume. The canonical content lives in JSONB `data`."""

    __tablename__ = "resumes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    schema_version: Mapped[int] = mapped_column(Integer, default=CURRENT_SCHEMA_VERSION)
    data: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )