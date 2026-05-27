"""Add persisted site result snapshots.

Revision ID: 7f2b1d84c6a9
Revises: 4f55c5396e99
Create Date: 2026-05-12 00:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "7f2b1d84c6a9"
down_revision: str | None = "4f55c5396e99"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("scrape_items", sa.Column("site_results", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("scrape_items", "site_results")
