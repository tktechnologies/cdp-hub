#!/usr/bin/env python3
"""Print PostgreSQL scrape persistence stats (jobs, items, part_results).

Rows are created when work flows through the orchestrator after ``POST /api/v1/jobs``
(or Celery worker), not when you run ``scripts/interview_scraper_demo.py`` alone.

Requires ``DATABASE_URL`` / ``database_url`` from ``.env`` (default async Postgres URL).

Example::

    docker compose up -d postgres
    alembic upgrade head
    # submit a job via API, then:
    uv run --extra dev python scripts/inspect_scrape_db.py
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


async def _run() -> int:
    from sqlalchemy import func, select, text

    from src.models.database import (
        PartResultRecord,
        ScrapeItem,
        ScrapeJob,
        async_session,
    )

    try:
        from rich import box
        from rich.console import Console
        from rich.panel import Panel
        from rich.table import Table

        console = Console()
        use_rich = True
    except ImportError:
        use_rich = False
        console = None

    async with async_session() as session:
        n_jobs = await session.scalar(select(func.count()).select_from(ScrapeJob)) or 0
        n_items = await session.scalar(select(func.count()).select_from(ScrapeItem)) or 0
        n_parts = await session.scalar(select(func.count()).select_from(PartResultRecord)) or 0

        recent_jobs = (
            (
                await session.execute(
                    select(ScrapeJob).order_by(ScrapeJob.created_at.desc()).limit(8)
                )
            )
            .scalars()
            .all()
        )

        recent_parts = (
            await session.execute(
                select(PartResultRecord, ScrapeItem.sku)
                .join(ScrapeItem, PartResultRecord.item_id == ScrapeItem.id)
                .order_by(PartResultRecord.scraped_at.desc())
                .limit(10)
            )
        ).all()

        audit_rows: list[tuple[str, list[dict[str, object]]]] = []
        if os.environ.get("CDP_DB_AUDIT") == "1":
            audit_queries = [
                (
                    "job_status_counts",
                    """
                    select status, count(*) as count
                    from scrape_jobs
                    group by status
                    order by status
                    """,
                ),
                (
                    "site_status_counts",
                    """
                    select coalesce(e.value->>'site', '(none)') as site,
                           coalesce(e.value->>'status', '(none)') as status,
                           count(*) as count
                    from scrape_items i
                    left join lateral json_array_elements(i.site_results) as e(value) on true
                    group by 1, 2
                    order by 1, 2
                    """,
                ),
                (
                    "terminal_jobs_missing_items",
                    """
                    select count(*) as count
                    from scrape_jobs j
                    left join scrape_items i on i.job_id = j.id
                    where j.total_items > 0
                      and j.status in ('completed', 'failed', 'partial')
                      and i.id is null
                    """,
                ),
                (
                    "orphan_items",
                    """
                    select count(*) as count
                    from scrape_items i
                    left join scrape_jobs j on j.id = i.job_id
                    where j.id is null
                    """,
                ),
                (
                    "orphan_part_results",
                    """
                    select count(*) as count
                    from part_results p
                    left join scrape_items i on i.id = p.item_id
                    where i.id is null
                    """,
                ),
                (
                    "invalid_part_result_required_fields",
                    """
                    select count(*) as count
                    from part_results
                    where coalesce(sku_searched, '') = ''
                       or coalesce(sku_found, '') = ''
                       or coalesce(site, '') = ''
                       or coalesce(site_name, '') = ''
                       or coalesce(currency, '') not in ('BRL', 'USD', 'EUR')
                       or exact_match is null
                       or scraped_at is null
                    """,
                ),
                (
                    "result_rows_by_site",
                    """
                    select site,
                           count(*) as rows,
                           count(*) filter (where exact_match is true and price > 0) as exact_priced,
                           min(scraped_at)::text as oldest,
                           max(scraped_at)::text as newest
                    from part_results
                    group by site
                    order by site
                    """,
                ),
            ]
            for name, sql in audit_queries:
                rows = (await session.execute(text(sql))).mappings().all()
                audit_rows.append((name, [dict(row) for row in rows]))

    if use_rich and console is not None:
        console.print(
            Panel.fit(
                "[bold]CDP Scraper — database snapshot[/]\n"
                "[dim]Counts reflect orchestrator-persisted jobs only.[/]",
                border_style="blue",
                box=box.DOUBLE,
            )
        )
        t = Table(title="Totals", box=box.ROUNDED)
        t.add_column("Table", style="cyan")
        t.add_column("Rows", justify="right")
        t.add_row("scrape_jobs", str(n_jobs))
        t.add_row("scrape_items", str(n_items))
        t.add_row("part_results", str(n_parts))
        console.print(t)

        jt = Table(title="Latest scrape_jobs", box=box.SIMPLE_HEAD)
        jt.add_column("id", overflow="ellipsis", max_width=14)
        jt.add_column("status", width=12)
        jt.add_column("items ok/fail", justify="right")
        jt.add_column("created", max_width=22)
        for job in recent_jobs:
            jt.add_row(
                job.id[:12] + "…",
                job.status,
                f"{job.items_succeeded or 0}/{job.items_failed or 0}",
                str(job.created_at)[:19] if job.created_at else "",
            )
        console.print(jt)

        pt = Table(title="Latest part_results (joined SKU)", box=box.SIMPLE_HEAD)
        pt.add_column("site", width=10)
        pt.add_column("item SKU", max_width=14)
        pt.add_column("price", justify="right", width=10)
        pt.add_column("title", overflow="ellipsis", max_width=40)
        for row in recent_parts:
            part, sku = row[0], row[1]
            title = (part.raw_title or "")[:80]
            price_s = "" if part.price is None else f"{part.price:.2f}"
            pt.add_row(part.site, sku[:14], price_s, title)
        console.print(pt)

        if audit_rows:
            for name, rows in audit_rows:
                audit_table = Table(title=f"Audit: {name}", box=box.SIMPLE_HEAD)
                columns = list(rows[0].keys()) if rows else ["result"]
                for column in columns:
                    audit_table.add_column(column)
                if rows:
                    for row in rows:
                        audit_table.add_row(*(str(row.get(column, "")) for column in columns))
                else:
                    audit_table.add_row("(no rows)")
                console.print(audit_table)
    else:
        print("--- CDP Scraper DB snapshot (plain) ---")
        print(f"scrape_jobs:   {n_jobs}")
        print(f"scrape_items:  {n_items}")
        print(f"part_results:  {n_parts}")
        print("\nLatest jobs:")
        for job in recent_jobs:
            print(
                f"  {job.id[:10]}…  {job.status:12}  ok/fail={job.items_succeeded}/{job.items_failed}  "
                f"{str(job.created_at)[:19] if job.created_at else ''}"
            )
        print("\nLatest part rows:")
        for row in recent_parts:
            part, sku = row[0], row[1]
            print(
                f"  {part.site:10}  sku={sku[:16]:<16}  price={part.price}  {(part.raw_title or '')[:50]}"
            )
        for name, rows in audit_rows:
            print(f"\nAudit: {name}")
            for row in rows:
                print(f"  {row}")

    if n_jobs == 0 and n_parts == 0:
        msg = (
            "\nNo rows yet. Submit a job through the API (e.g. POST /api/v1/jobs with X-API-Key) "
            "or run the stack with JOB_EXECUTION_BACKEND=local and poll GET /api/v1/jobs/{id}."
        )
        if use_rich and console is not None:
            console.print(f"[yellow]{msg}[/]")
        else:
            print(msg)

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database-url",
        default=os.environ.get("DATABASE_URL", ""),
        help="Override async DB URL for this run (otherwise from settings / .env).",
    )
    parser.add_argument(
        "--audit",
        action="store_true",
        help="Print extra read-only persistence integrity checks.",
    )
    args = parser.parse_args()
    if args.database_url:
        os.environ["DATABASE_URL"] = args.database_url
    if args.audit:
        os.environ["CDP_DB_AUDIT"] = "1"

    return asyncio.run(_run())


if __name__ == "__main__":
    raise SystemExit(main())
