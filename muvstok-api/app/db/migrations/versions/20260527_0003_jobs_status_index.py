"""Add status index on muvstok_jobs for worker and API filters.

Revision ID: 20260527_0003
Revises: 20260519_0002
Create Date: 2026-05-27
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260527_0003"
down_revision: str | None = "20260519_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_muvstok_jobs_status",
        "muvstok_jobs",
        ["status"],
        unique=False,
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_index("ix_muvstok_jobs_status", table_name="muvstok_jobs", if_exists=True)
