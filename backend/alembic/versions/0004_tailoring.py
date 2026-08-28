"""Immutable ResumeVersion snapshots and persisted Tailored Resumes.

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-28

T5 (Tailoring): the ResumeVersion snapshot (ADR-0004) captured when a
tailoring job starts, and the persisted Tailored Resume for the review step.
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "resume_versions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("resume_id", sa.String(length=36), nullable=False, index=True),
        sa.Column("data", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "tailored_resumes",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "job_description_id",
            sa.String(length=36),
            sa.ForeignKey("job_descriptions.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column("resume_version_id", sa.String(length=36), nullable=False),
        sa.Column("resume_id", sa.String(length=36), nullable=False),
        sa.Column("data", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_tailored_resumes_job_description_id",
        "tailored_resumes",
        ["job_description_id"],
    )
    op.create_index("ix_resume_versions_resume_id", "resume_versions", ["resume_id"])


def downgrade() -> None:
    op.drop_index("ix_resume_versions_resume_id", table_name="resume_versions")
    op.drop_index(
        "ix_tailored_resumes_job_description_id", table_name="tailored_resumes"
    )
    op.drop_table("tailored_resumes")
    op.drop_table("resume_versions")