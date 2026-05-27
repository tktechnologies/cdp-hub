"""Run one real scraper/SKU case in Playwright, optionally headed and slowed down."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import shlex
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]

SITE_CHOICES = (
    "gm",
    "ml",
    "vw",
    "eu",
    "goparts",
    "procurapecas",
    "pecadireta",
    "ebay",
    "melibox",
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", required=True, choices=SITE_CHOICES)
    parser.add_argument("--sku", required=True)
    parser.add_argument("--brand", default="")
    parser.add_argument("--timeout-seconds", type=float, default=120.0)
    parser.add_argument("--slow-mo-ms", type=int, default=250)
    parser.add_argument("--hold-seconds", type=float, default=10.0)
    parser.add_argument("--headless", action="store_true", help="Run headless instead of headed.")
    parser.add_argument(
        "--output",
        default="docs/validation/latest_headed_scraper_results.json",
        help="JSON file where case results are appended.",
    )
    return parser.parse_args()


def _configure_environment(args: argparse.Namespace) -> None:
    os.environ["PLAYWRIGHT_HEADLESS"] = "true" if args.headless else "false"
    os.environ["PLAYWRIGHT_SLOW_MO_MS"] = str(args.slow_mo_ms)
    os.environ.setdefault("MOCK_SCRAPERS", "false")
    os.environ.setdefault("PROXY_ROTATION_ENABLED", "false")


def _summarize_result(
    *,
    command: str,
    site: str,
    sku: str,
    brand: str,
    result: Any,
    started_at: datetime,
) -> dict[str, Any]:
    payload = result.model_dump(mode="json")
    parts = payload.get("results", [])
    priced_parts = [
        part for part in parts
        if isinstance(part.get("price"), int | float) and part.get("price") > 0
    ]
    first_price = priced_parts[0] if priced_parts else None

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "started_at": started_at.isoformat(),
        "command": command,
        "site": site,
        "sku": sku,
        "brand": brand,
        "success": payload.get("status") == "success",
        "price": first_price.get("price") if first_price else None,
        "currency": first_price.get("currency") if first_price else None,
        "status": payload.get("status"),
        "error_message": payload.get("error_message", ""),
        "search_time_ms": payload.get("search_time_ms", 0),
        "total_results": len(parts),
        "exact_results": sum(1 for part in parts if part.get("exact_match") is True),
        "prices": [
            {
                "price": part.get("price"),
                "currency": part.get("currency"),
                "sku_found": part.get("sku_found"),
                "exact_match": part.get("exact_match"),
                "condition": part.get("condition"),
                "availability": part.get("availability"),
                "origin": part.get("origin"),
                "title": part.get("raw_title"),
                "url": part.get("product_url"),
            }
            for part in parts
        ],
        "raw_site_result": payload,
    }


def _append_output(output_path: Path, summary: dict[str, Any]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    existing: dict[str, Any]
    if output_path.exists():
        existing = json.loads(output_path.read_text(encoding="utf-8"))
    else:
        existing = {
            "generated_for": "headed one-case scraper validation",
            "cases": [],
        }

    existing["updated_at"] = datetime.now(UTC).isoformat()
    existing.setdefault("cases", []).append(summary)
    output_path.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")


async def _run(args: argparse.Namespace) -> int:
    sys.path.insert(0, str(PROJECT_ROOT))

    from src.models.schemas import SiteId, SiteResult
    from src.scrapers import (
        ARCHIVED_SCRAPER_REGISTRY,
        SCRAPER_REGISTRY,
        get_scraper,
        shutdown_all_scrapers,
    )

    started_at = datetime.now(UTC)
    command = (
        f"UV_CACHE_DIR=/tmp/uv-cache PLAYWRIGHT_HEADLESS={os.environ['PLAYWRIGHT_HEADLESS']} "
        f"PLAYWRIGHT_SLOW_MO_MS={os.environ['PLAYWRIGHT_SLOW_MO_MS']} "
        f"MOCK_SCRAPERS={os.environ.get('MOCK_SCRAPERS', 'false')} "
        f"PROXY_ROTATION_ENABLED={os.environ.get('PROXY_ROTATION_ENABLED', 'false')} "
        f"uv run --extra dev python {shlex.join(sys.argv)}"
    )

    page = None
    archived_scraper = None
    result: SiteResult
    try:
        site_id = SiteId(args.site)
        if site_id in SCRAPER_REGISTRY:
            scraper = await get_scraper(site_id)
        else:
            scraper_class = ARCHIVED_SCRAPER_REGISTRY.get(site_id)
            if scraper_class is None:
                raise ValueError(f"No scraper available for site: {site_id.value}")
            archived_scraper = scraper_class()
            await archived_scraper.initialize()
            scraper = archived_scraper
        assert scraper._context is not None

        page = await scraper._context.new_page()
        start_time = time.monotonic()
        try:
            if not await scraper.ensure_authenticated(page):
                result = SiteResult(
                    site=scraper.site_id,
                    site_name=scraper.site_name,
                    status="error",
                    error_message="Authentication failed",
                    search_time_ms=int((time.monotonic() - start_time) * 1000),
                )
            else:
                normalized_sku = scraper._normalize_sku(args.sku, args.brand)
                raw_results = await asyncio.wait_for(
                    scraper._search_with_retry(page, normalized_sku, args.brand),
                    timeout=args.timeout_seconds,
                )
                result = scraper._site_result_from_search(
                    raw_results,
                    int((time.monotonic() - start_time) * 1000),
                )
        except TimeoutError:
            result = SiteResult(
                site=scraper.site_id,
                site_name=scraper.site_name,
                status="timeout",
                error_message=f"Timed out after {args.timeout_seconds} seconds.",
                search_time_ms=int((time.monotonic() - start_time) * 1000),
            )
        except Exception as exc:
            result = SiteResult(
                site=scraper.site_id,
                site_name=scraper.site_name,
                status="error",
                error_message=str(exc),
                search_time_ms=int((time.monotonic() - start_time) * 1000),
            )

        summary = _summarize_result(
            command=command,
            site=args.site,
            sku=args.sku,
            brand=args.brand,
            result=result,
            started_at=started_at,
        )
        _append_output(Path(args.output), summary)
        console_summary = {
            key: value for key, value in summary.items()
            if key not in {"raw_site_result", "prices"}
        }
        console_summary["prices"] = summary["prices"][:3]
        console_summary["prices_truncated"] = max(len(summary["prices"]) - 3, 0)
        print(json.dumps(console_summary, indent=2, ensure_ascii=False))

        if args.hold_seconds > 0:
            await asyncio.sleep(args.hold_seconds)

        return 0
    finally:
        if page is not None:
            await page.close()
        if archived_scraper is not None:
            await archived_scraper.shutdown()
        await shutdown_all_scrapers()


def main() -> int:
    args = _parse_args()
    _configure_environment(args)
    return asyncio.run(_run(args))


if __name__ == "__main__":
    raise SystemExit(main())
