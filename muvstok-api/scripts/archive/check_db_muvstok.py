#!/usr/bin/env python3
"""Quick Azure DB health check for Muvstok tables (run inside cdp-muv-api or with DATABASE_URL)."""
from __future__ import annotations

import asyncio
import os
import sys

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


async def main() -> int:
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        print("DATABASE_URL not set", file=sys.stderr)
        return 1

    engine = create_async_engine(url)
    try:
        async with engine.connect() as conn:
            row = await conn.execute(
                text(
                    "SELECT current_database(), current_user, "
                    "count(*) FROM information_schema.tables WHERE table_schema = 'public'"
                )
            )
            db, user, table_count = row.fetchone()
            print(f"database={db} user={user} public_tables={table_count}")

            for table in (
                "product_price_snapshots",
                "muvstok_raw_demand_snapshots",
                "muvstok_api_data",
            ):
                try:
                    count = await conn.scalar(text(f"SELECT count(*) FROM {table}"))
                    print(f"{table}.count={count}")
                except Exception as exc:
                    print(f"{table}.error={type(exc).__name__}: {exc}")

            recent = await conn.execute(
                text(
                    """
                    SELECT sku, captured_at, price, source_company_id
                    FROM product_price_snapshots
                    ORDER BY captured_at DESC NULLS LAST
                    LIMIT 8
                    """
                )
            )
            print("product_price_snapshots.recent:")
            for r in recent.fetchall():
                print(" ", r)

            recent_raw = await conn.execute(
                text(
                    """
                    SELECT sku, captured_at, source_company_id
                    FROM muvstok_raw_demand_snapshots
                    ORDER BY captured_at DESC NULLS LAST
                    LIMIT 5
                    """
                )
            )
            print("muvstok_raw_demand_snapshots.recent:")
            for r in recent_raw.fetchall():
                print(" ", r)

            by_day = await conn.execute(
                text(
                    """
                    SELECT date_trunc('day', captured_at)::date AS day, count(*) AS n
                    FROM product_price_snapshots
                    WHERE captured_at >= now() - interval '14 days'
                    GROUP BY 1
                    ORDER BY 1 DESC
                    LIMIT 7
                    """
                )
            )
            print("product_price_snapshots.by_day_last_14d:")
            for r in by_day.fetchall():
                print(" ", r)
    finally:
        await engine.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
