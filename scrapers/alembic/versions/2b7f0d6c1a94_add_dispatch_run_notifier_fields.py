"""Add aggregate notifier fields to dispatch_runs.

Revision ID: 2b7f0d6c1a94
Revises: 9d4e2a71b3c5
Create Date: 2026-06-08 10:30:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "2b7f0d6c1a94"
down_revision: str | None = "9d4e2a71b3c5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return column_name in {col["name"] for col in inspector.get_columns(table_name)}


def _add_column_if_missing(table_name: str, column: sa.Column) -> None:
    if not _has_column(table_name, column.name):
        op.add_column(table_name, column)


def upgrade() -> None:
    _add_column_if_missing("dispatch_runs", sa.Column("reply_channel", sa.Text(), nullable=True))
    _add_column_if_missing("dispatch_runs", sa.Column("reply_email", sa.Text(), nullable=True))
    _add_column_if_missing("dispatch_runs", sa.Column("command_origin", sa.Text(), nullable=True))
    _add_column_if_missing(
        "dispatch_runs",
        sa.Column("progress_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    _add_column_if_missing(
        "dispatch_runs",
        sa.Column("delivery_mode", sa.String(length=32), nullable=False, server_default="legacy"),
    )
    _add_column_if_missing(
        "dispatch_runs",
        sa.Column("sheet_row_numbers", sa.JSON(), nullable=False, server_default="[]"),
    )
    _add_column_if_missing("dispatch_runs", sa.Column("scraper_summary", sa.JSON(), nullable=True))
    _add_column_if_missing("dispatch_runs", sa.Column("stokapi_summary", sa.JSON(), nullable=True))
    _add_column_if_missing(
        "dispatch_runs",
        sa.Column("scraper_completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    _add_column_if_missing(
        "dispatch_runs",
        sa.Column("stokapi_completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    _add_column_if_missing(
        "dispatch_runs",
        sa.Column("final_notification_status", sa.String(length=32), nullable=True),
    )
    _add_column_if_missing(
        "dispatch_runs",
        sa.Column("final_notified_at", sa.DateTime(timezone=True), nullable=True),
    )
    _add_column_if_missing(
        "dispatch_runs",
        sa.Column("final_notification_attempts", sa.Integer(), nullable=False, server_default="0"),
    )
    _add_column_if_missing("dispatch_runs", sa.Column("final_channel", sa.String(length=20), nullable=True))
    _add_column_if_missing("dispatch_runs", sa.Column("final_error", sa.Text(), nullable=True))


def downgrade() -> None:
    for column_name in (
        "final_error",
        "final_channel",
        "final_notification_attempts",
        "final_notified_at",
        "final_notification_status",
        "stokapi_completed_at",
        "scraper_completed_at",
        "stokapi_summary",
        "scraper_summary",
        "sheet_row_numbers",
        "delivery_mode",
        "progress_enabled",
        "command_origin",
        "reply_email",
        "reply_channel",
    ):
        if _has_column("dispatch_runs", column_name):
            op.drop_column("dispatch_runs", column_name)
