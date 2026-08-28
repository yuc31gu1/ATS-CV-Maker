import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.domain.resume import CURRENT_SCHEMA_VERSION
from app.time import utcnow


class ResumeRow(Base):
    """Persisted Master Resume. The canonical content lives in JSONB `data`."""

    __tablename__ = "resumes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    schema_version: Mapped[int] = mapped_column(Integer, default=CURRENT_SCHEMA_VERSION)
    data: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class JobDescription(Base):
    __tablename__ = "job_descriptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[str | None] = mapped_column(String(255), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    jd_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class JobAnalysis(Base):
    __tablename__ = "job_analyses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    job_description_id: Mapped[str] = mapped_column(
        ForeignKey("job_descriptions.id"), unique=True, index=True
    )
    role: Mapped[str] = mapped_column(String(255), nullable=False)
    seniority: Mapped[str | None] = mapped_column(String(64), nullable=True)
    requirements: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    type: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="PENDING", index=True)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class MatchResultRow(Base):
    """Persisted requirement–evidence match result, keyed by job description.

    MATCH runs synchronously (ADR-0003); the row lets the stepper re-fetch the
    result on back-navigation without recomputing or re-running anything.
    """

    __tablename__ = "job_match_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    job_description_id: Mapped[str] = mapped_column(
        ForeignKey("job_descriptions.id"), unique=True, index=True
    )
    resume_id: Mapped[str] = mapped_column(String(36), nullable=False)
    matches: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)