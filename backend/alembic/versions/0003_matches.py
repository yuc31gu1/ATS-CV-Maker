"""Persisted requirement–evidence match results.

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-28
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "job_match_results",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "job_description_id",
            sa.String(length=36),
            sa.ForeignKey("job_descriptions.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column("resume_id", sa.String(length=36), nullable=False),
        sa.Column("matches", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_job_match_results_job_description_id",
        "job_match_results",
        ["job_description_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_job_match_results_job_description_id", table_name="job_match_results"
    )
    op.drop_table("job_match_results")