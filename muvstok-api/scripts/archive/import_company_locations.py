#!/usr/bin/env python3
"""Import company/dealership location metadata into API Diversos Postgres."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import get_settings  # noqa: E402
from app.services.dealership_directory import parse_company_location_csv  # noqa: E402


def _read_local_text(csv_path: Path) -> str:
    return csv_path.read_text(encoding="utf-8-sig")


async def _read_text(*, csv_path: Path | None, csv_url: str, timeout_seconds: float) -> str:
    if csv_path is not None:
        return _read_local_text(csv_path)
    if not csv_url:
        raise ValueError("Provide --csv-path or --csv-url, or configure MUVSTOK_DEALERSHIP_DIRECTORY_URL.")
    async with httpx.AsyncClient(timeout=timeout_seconds, follow_redirects=True) as client:
        response = await client.get(csv_url)
        response.raise_for_status()
        return response.text


async def main_async(args: argparse.Namespace) -> int:
    settings = get_settings()
    text = await _read_text(
        csv_path=args.csv_path,
        csv_url=args.csv_url or settings.muvstok_dealership_directory_url,
        timeout_seconds=settings.muvstok_timeout_seconds,
    )
    records = parse_company_location_csv(text)
    if args.dry_run:
        print(
            json.dumps(
                {
                    "source": str(args.csv_path) if args.csv_path else "url",
                    "parsed_records": len(records),
                    "dry_run": True,
                },
                ensure_ascii=False,
            )
        )
        return 0

    from app.db.session import AsyncSessionLocal
    from app.repositories.company_location_repository import CompanyLocationRepository

    async with AsyncSessionLocal() as session:
        repo = CompanyLocationRepository(session)
        upserted = await repo.upsert_many(records)
        await session.commit()
        total = await repo.count()

    print(
        json.dumps(
            {
                "source": str(args.csv_path) if args.csv_path else "url",
                "parsed_records": len(records),
                "upserted_records": upserted,
                "table_records": total,
            },
            ensure_ascii=False,
        )
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv-path", type=Path, help="Local CSV export to import.")
    parser.add_argument("--csv-url", default="", help="CSV URL to download and import.")
    parser.add_argument("--dry-run", action="store_true", help="Parse input without writing DB rows.")
    args = parser.parse_args()
    try:
        return asyncio.run(main_async(args))
    except Exception as exc:
        print(f"import_company_locations failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
