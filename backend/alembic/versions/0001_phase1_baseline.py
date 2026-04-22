"""phase1 baseline

Revision ID: 0001_phase1_baseline
Revises:
Create Date: 2026-04-22
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0001_phase1_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "jobs",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("team_id", sa.String(length=64), nullable=False),
        sa.Column("client_slug", sa.String(length=255), nullable=False),
        sa.Column("format_seconds", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("stage", sa.String(length=64), nullable=False),
        sa.Column("clip_total", sa.Integer(), nullable=False),
        sa.Column("clip_1_approved", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_by", sa.String(length=255), nullable=True),
        sa.Column("idempotency_key", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_jobs_team_id", "jobs", ["team_id"])
    op.create_index("ix_jobs_idempotency_key", "jobs", ["idempotency_key"])

    op.create_table(
        "run_events",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("job_id", sa.String(length=64), nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("trace_id", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_run_events_job_id", "run_events", ["job_id"])
    op.create_index("ix_run_events_trace_id", "run_events", ["trace_id"])


def downgrade() -> None:
    op.drop_index("ix_run_events_trace_id", table_name="run_events")
    op.drop_index("ix_run_events_job_id", table_name="run_events")
    op.drop_table("run_events")

    op.drop_index("ix_jobs_idempotency_key", table_name="jobs")
    op.drop_index("ix_jobs_team_id", table_name="jobs")
    op.drop_table("jobs")
