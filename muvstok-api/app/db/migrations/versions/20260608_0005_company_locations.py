"""Add company location directory table.

Revision ID: 20260608_0005
Revises: 20260529_0004
Create Date: 2026-06-08
"""

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260608_0005"
down_revision: str | None = "20260529_0004"
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
        "company_locations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("id_empresa", sa.String(length=50), nullable=False),
        sa.Column("id_grupoempresa", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("projeto", sa.String(length=100), nullable=False, server_default=""),
        sa.Column("montadora", sa.String(length=100), nullable=False, server_default=""),
        sa.Column("nm_corporacao", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("grupo_empresa", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("cnpj", sa.String(length=14), nullable=False, server_default=""),
        sa.Column("nome_fantasia", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("apelido", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("cep", sa.String(length=16), nullable=False, server_default=""),
        sa.Column("endereco", sa.String(length=300), nullable=False, server_default=""),
        sa.Column("numero", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("uf", sa.String(length=2), nullable=False, server_default=""),
        sa.Column("cidade", sa.String(length=150), nullable=False, server_default=""),
        sa.Column("bairro", sa.String(length=150), nullable=False, server_default=""),
        sa.Column("metadata", postgresql.JSONB(), server_default=jsonb_default(), nullable=False),
        *timestamp_columns(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id_empresa", name="uq_company_locations_id_empresa"),
    )
    op.create_index("ix_company_locations_cnpj", "company_locations", ["cnpj"])
    op.create_index("ix_company_locations_uf", "company_locations", ["uf"])
    op.create_index("ix_company_locations_montadora", "company_locations", ["montadora"])


def downgrade() -> None:
    op.drop_index("ix_company_locations_montadora", table_name="company_locations")
    op.drop_index("ix_company_locations_uf", table_name="company_locations")
    op.drop_index("ix_company_locations_cnpj", table_name="company_locations")
    op.drop_table("company_locations")
