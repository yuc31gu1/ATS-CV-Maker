"""Resumes, job descriptions, job analyses, and background jobs.

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-28

Reconciled the T2 (resumes) and T3 (job descriptions/job analyses/jobs)
migrations, which were both authored as revision 0002 on parallel branches,
into a single revision so the version graph stays linear.
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "resumes",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.Column("data", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "job_descriptions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("company", sa.String(length=255), nullable=True),
        sa.Column("role", sa.String(length=255), nullable=True),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("jd_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "job_analyses",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "job_description_id",
            sa.String(length=36),
            sa.ForeignKey("job_descriptions.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column("role", sa.String(length=255), nullable=False),
        sa.Column("seniority", sa.String(length=64), nullable=True),
        sa.Column("requirements", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_job_analyses_job_description_id", "job_analyses", ["job_description_id"]
    )
    op.create_table(
        "jobs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("type", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column("result", JSONB(), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_jobs_status", "jobs", ["status"])


def downgrade() -> None:
    op.drop_index("ix_jobs_status", table_name="jobs")
    op.drop_table("jobs")
    op.drop_index("ix_job_analyses_job_description_id", table_name="job_analyses")
    op.drop_table("job_analyses")
    op.drop_table("job_descriptions")
    op.drop_table("resumes")