"""Persisted Generated Resumes (LaTeX + PDF delivery bundles).

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-28

T6 (Document Generation): the Generated Resume row persists the delivery
bundle for one job — Tailored Resume rendered to LaTeX and compiled to PDF —
pinned to the immutable ResumeVersion (ADR-0004). The LaTeX source and PDF
bytes live in the StorageService under keys stored in ``data``.
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "generated_resumes",
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
        "ix_generated_resumes_job_description_id",
        "generated_resumes",
        ["job_description_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_generated_resumes_job_description_id", table_name="generated_resumes"
    )
    op.drop_table("generated_resumes")