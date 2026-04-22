"""connector persistence tables

Revision ID: 0002_connector_persistence
Revises: 0001_phase1_baseline
Create Date: 2026-04-22
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0002_connector_persistence"
down_revision = "0001_phase1_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "connector_oauth_states",
        sa.Column("state", sa.String(length=255), primary_key=True),
        sa.Column("team_id", sa.String(length=64), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_connector_oauth_states_team_id", "connector_oauth_states", ["team_id"])

    op.create_table(
        "asset_sources",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("team_id", sa.String(length=64), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("external_account_id", sa.String(length=255), nullable=False),
        sa.Column("access_token", sa.String(length=2048), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_asset_sources_team_id", "asset_sources", ["team_id"])

    op.create_table(
        "asset_sync_jobs",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("team_id", sa.String(length=64), nullable=False),
        sa.Column("source_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("synced_count", sa.Integer(), nullable=False),
        sa.Column("next_page_token", sa.String(length=255), nullable=True),
        sa.Column("error_message", sa.String(length=1024), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_asset_sync_jobs_team_id", "asset_sync_jobs", ["team_id"])
    op.create_index("ix_asset_sync_jobs_source_id", "asset_sync_jobs", ["source_id"])

    op.create_table(
        "connector_assets",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("source_id", sa.String(length=64), nullable=False),
        sa.Column("team_id", sa.String(length=64), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=512), nullable=False),
        sa.Column("mime_type", sa.String(length=128), nullable=False),
        sa.Column("modified_time", sa.String(length=128), nullable=False),
        sa.Column("web_view_link", sa.String(length=2048), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_connector_assets_source_id", "connector_assets", ["source_id"])
    op.create_index("ix_connector_assets_team_id", "connector_assets", ["team_id"])
    op.create_unique_constraint(
        "uq_connector_assets_source_external",
        "connector_assets",
        ["source_id", "external_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_connector_assets_source_external", "connector_assets", type_="unique")
    op.drop_index("ix_connector_assets_team_id", table_name="connector_assets")
    op.drop_index("ix_connector_assets_source_id", table_name="connector_assets")
    op.drop_table("connector_assets")

    op.drop_index("ix_asset_sync_jobs_source_id", table_name="asset_sync_jobs")
    op.drop_index("ix_asset_sync_jobs_team_id", table_name="asset_sync_jobs")
    op.drop_table("asset_sync_jobs")

    op.drop_index("ix_asset_sources_team_id", table_name="asset_sources")
    op.drop_table("asset_sources")

    op.drop_index("ix_connector_oauth_states_team_id", table_name="connector_oauth_states")
    op.drop_table("connector_oauth_states")
