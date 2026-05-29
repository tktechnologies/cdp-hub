#!/usr/bin/env python3
"""One-off: apply 20260529_0004 (drop job_id+sku unique) using app DATABASE_URL."""
from __future__ import annotations

import sys

from sqlalchemy import create_engine, text

from app.core.config import get_settings

MIGRATION = "20260529_0004"
CONSTRAINT = "uq_muvstok_job_items_job_sku"


def main() -> int:
    settings = get_settings()
    url = settings.database_url
    if url.startswith("postgresql+psycopg://"):
        url = "postgresql+psycopg://" + url.split("postgresql+psycopg://", 1)[1]
    elif url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url.split("postgresql://", 1)[1]

    engine = create_engine(url, pool_pre_ping=True)
    with engine.begin() as conn:
        current = conn.execute(
            text("SELECT version_num FROM muvstok_alembic_version LIMIT 1")
        ).scalar()
        print(f"Current alembic version: {current}")

        if current == MIGRATION:
            print("Already at head.")
            return 0

        if current not in (None, "20260527_0003"):
            print(f"Unexpected version {current!r}", file=sys.stderr)
            return 1

        conn.execute(
            text(f"ALTER TABLE muvstok_job_items DROP CONSTRAINT IF EXISTS {CONSTRAINT}")
        )
        if current is None:
            conn.execute(
                text("INSERT INTO muvstok_alembic_version (version_num) VALUES (:v)"),
                {"v": MIGRATION},
            )
        else:
            conn.execute(
                text("UPDATE muvstok_alembic_version SET version_num = :v"),
                {"v": MIGRATION},
            )
        print(f"Migration {MIGRATION} applied.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
