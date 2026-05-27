"""Add query indexes for jobs and dispatch runs.

Revision ID: 9d4e2a71b3c5
Revises: 8a3c1e95f2b0
Create Date: 2026-05-27 12:00:00.000000
"""
from collections.abc import Sequence

from alembic import op

revision: str = "9d4e2a71b3c5"
down_revision: str | None = "8a3c1e95f2b0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_scrape_jobs_status_created_at",
        "scrape_jobs",
        ["status", "created_at"],
        unique=False,
        if_not_exists=True,
    )
    op.create_index(
        "ix_dispatch_runs_chat_id",
        "dispatch_runs",
        ["chat_id"],
        unique=False,
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_index("ix_dispatch_runs_chat_id", table_name="dispatch_runs", if_exists=True)
    op.drop_index("ix_scrape_jobs_status_created_at", table_name="scrape_jobs", if_exists=True)
