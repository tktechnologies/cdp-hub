"""Add seller metadata fields to part_results.

Revision ID: 3c9a6b4e0d12
Revises: 2b7f0d6c1a94
Create Date: 2026-06-08 10:45:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "3c9a6b4e0d12"
down_revision: str | None = "2b7f0d6c1a94"
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
    _add_column_if_missing("part_results", sa.Column("seller_uf", sa.String(length=2), nullable=True))
    _add_column_if_missing("part_results", sa.Column("seller_company_name", sa.String(length=200), nullable=True))
    _add_column_if_missing("part_results", sa.Column("seller_cnpj", sa.String(length=14), nullable=True))


def downgrade() -> None:
    for column_name in ("seller_cnpj", "seller_company_name", "seller_uf"):
        if _has_column("part_results", column_name):
            op.drop_column("part_results", column_name)
