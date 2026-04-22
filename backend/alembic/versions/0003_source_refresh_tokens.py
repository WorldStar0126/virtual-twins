"""add refresh token fields to asset sources

Revision ID: 0003_source_refresh_tokens
Revises: 0002_connector_persistence
Create Date: 2026-04-22
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0003_source_refresh_tokens"
down_revision = "0002_connector_persistence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("asset_sources", sa.Column("refresh_token", sa.String(length=2048), nullable=True))
    op.add_column(
        "asset_sources",
        sa.Column("access_token_expires_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("asset_sources", "access_token_expires_at")
    op.drop_column("asset_sources", "refresh_token")
