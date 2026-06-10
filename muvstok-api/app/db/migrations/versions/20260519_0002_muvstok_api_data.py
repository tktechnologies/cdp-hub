"""Add dedicated Muvstok API data table.

Revision ID: 20260519_0002
Revises: 20260503_0001
Create Date: 2026-05-19
"""

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260519_0002"
down_revision: str | None = "20260503_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def jsonb_default() -> sa.TextClause:
    return sa.text("'{}'::jsonb")


def timestamp_columns() -> list[sa.Column[Any]]:
    return [
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "muvstok_api_data",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("correlation_id", sa.String(length=100), nullable=False),
        sa.Column("sku", sa.String(length=128), nullable=False),
        sa.Column("response_status", sa.String(length=50), nullable=False),
        sa.Column(
            "request_metadata",
            postgresql.JSONB(),
            server_default=jsonb_default(),
            nullable=False,
        ),
        sa.Column(
            "response_metadata",
            postgresql.JSONB(),
            server_default=jsonb_default(),
            nullable=False,
        ),
        sa.Column("muvstok_payload", postgresql.JSONB(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(), server_default=jsonb_default(), nullable=False),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(["job_id"], ["muvstok_jobs.id"]),
        sa.ForeignKeyConstraint(["job_item_id"], ["muvstok_job_items.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_item_id", name="uq_muvstok_api_data_job_item_id"),
    )
    op.create_index("ix_muvstok_api_data_correlation_id", "muvstok_api_data", ["correlation_id"])
    op.create_index("ix_muvstok_api_data_job_id", "muvstok_api_data", ["job_id"])
    op.create_index("ix_muvstok_api_data_job_item_id", "muvstok_api_data", ["job_item_id"])
    op.create_index("ix_muvstok_api_data_job_sku", "muvstok_api_data", ["job_id", "sku"])
    op.create_index("ix_muvstok_api_data_sku", "muvstok_api_data", ["sku"])
    op.create_index("ix_muvstok_api_data_sku_created_at", "muvstok_api_data", ["sku", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_muvstok_api_data_sku_created_at", table_name="muvstok_api_data")
    op.drop_index("ix_muvstok_api_data_sku", table_name="muvstok_api_data")
    op.drop_index("ix_muvstok_api_data_job_sku", table_name="muvstok_api_data")
    op.drop_index("ix_muvstok_api_data_job_item_id", table_name="muvstok_api_data")
    op.drop_index("ix_muvstok_api_data_job_id", table_name="muvstok_api_data")
    op.drop_index("ix_muvstok_api_data_correlation_id", table_name="muvstok_api_data")
    op.drop_table("muvstok_api_data")
