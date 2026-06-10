"""Drop (job_id, sku) unique constraint on muvstok_job_items.

Duplicate SKUs within a single job are now stored as separate items so a job
with N input SKUs yields N callback results (duplicates served from cache).

Revision ID: 20260529_0004
Revises: 20260527_0003
Create Date: 2026-05-29
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260529_0004"
down_revision: str | None = "20260527_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CONSTRAINT_NAME = "uq_muvstok_job_items_job_sku"
TABLE_NAME = "muvstok_job_items"


def upgrade() -> None:
    op.execute(f"ALTER TABLE {TABLE_NAME} DROP CONSTRAINT IF EXISTS {CONSTRAINT_NAME}")


def downgrade() -> None:
    # Recreating the constraint requires that no duplicate (job_id, sku) rows exist.
    op.create_unique_constraint(CONSTRAINT_NAME, TABLE_NAME, ["job_id", "sku"])
