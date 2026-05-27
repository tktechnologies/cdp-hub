"""Add scrape job progress counters and metadata column.

Revision ID: 8a3c1e95f2b0
Revises: 7f2b1d84c6a9
Create Date: 2026-05-27 00:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "8a3c1e95f2b0"
down_revision: str | None = "7f2b1d84c6a9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "scrape_jobs",
        sa.Column("items_processed", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("scrape_jobs", sa.Column("metadata", sa.JSON(), nullable=True))
    op.create_table(
        "dispatch_runs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("batch_group_id", sa.Text(), nullable=False),
        sa.Column("chat_id", sa.Text(), nullable=True),
        sa.Column("command_route", sa.Text(), nullable=True),
        sa.Column("scraper_job_ids", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("stokapi_job_id", sa.Text(), nullable=True),
        sa.Column("total_skus", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("estimated_seconds", sa.Integer(), nullable=True),
        sa.Column("scraper_status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("stokapi_status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("last_progress_pct", sa.Float(), nullable=False, server_default="0"),
        sa.Column("last_notified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("progress_message_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_dispatch_runs_chat_id", "dispatch_runs", ["chat_id"])
    op.create_index("ix_dispatch_runs_batch_group_id", "dispatch_runs", ["batch_group_id"])


def downgrade() -> None:
    op.drop_index("ix_dispatch_runs_batch_group_id", table_name="dispatch_runs")
    op.drop_index("ix_dispatch_runs_chat_id", table_name="dispatch_runs")
    op.drop_table("dispatch_runs")
    op.drop_column("scrape_jobs", "metadata")
    op.drop_column("scrape_jobs", "items_processed")
