"""Run one local demo search per scraper and write raw JSON results.

This is intentionally looser than the real validation manifest. It is for
operator/agent discovery: search a known SKU on each scraper, capture prices,
status, timing, and any error message without asserting that a specific price
range must be returned.
"""

# ruff: noqa: E402,I001

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.models.schemas import SiteId, SiteResult
from src.scrapers import ARCHIVED_SCRAPER_REGISTRY, SCRAPER_REGISTRY, get_scraper, shutdown_all_scrapers
from src.services.result_formatter import _find_best_price


DEFAULT_CASES = [
    {"id": "gm-public", "site": SiteId.GM, "sku": "93240598", "brand": "GM"},
    {"id": "mercado-livre", "site": SiteId.MERCADO_LIVRE, "sku": "51766536", "brand": ""},
    {"id": "vw-official", "site": SiteId.VW, "sku": "5X9827550A", "brand": "VW"},
    {"id": "eu-imports", "site": SiteId.EUROPE, "sku": "03L115562", "brand": "VW"},
    {"id": "goparts", "site": SiteId.GOPARTS, "sku": "7091011", "brand": ""},
    {"id": "procurapecas", "site": SiteId.PROCURA_PECAS, "sku": "51766536", "brand": ""},
    {"id": "pecadireta", "site": SiteId.PECA_DIRETA, "sku": "7091011", "brand": ""},
    {"id": "ebay", "site": SiteId.EBAY, "sku": "5473368", "brand": ""},
    {"id": "melibox", "site": SiteId.MELIBOX, "sku": "51766536", "brand": ""},
]


async def _get_demo_scraper(site_id: SiteId):
    """Return active or archived scraper for local discovery demos."""
    if site_id in SCRAPER_REGISTRY:
        return await get_scraper(site_id), False

    scraper_class = ARCHIVED_SCRAPER_REGISTRY.get(site_id)
    if scraper_class is None:
        raise ValueError(f"No demo scraper available for site: {site_id.value}")
    scraper = scraper_class()
    await scraper.initialize()
    return scraper, True


def _summarize_site_result(case: dict[str, Any], site_result: SiteResult) -> dict[str, Any]:
    payload = site_result.model_dump(mode="json")
    parts = payload.get("results", [])
    best_price = _find_best_price(site_result.results)
    prices = [
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
    ]
    return {
        "case_id": case["id"],
        "site": case["site"].value,
        "sku": case["sku"],
        "brand": case["brand"],
        "job_id": None,
        "job_status": payload.get("status", "unknown"),
        "site_status": payload.get("status", "missing"),
        "error_message": payload.get("error_message", ""),
        "search_time_ms": payload.get("search_time_ms", 0),
        "total_results": len(parts),
        "best_price": best_price.model_dump(mode="json") if best_price else None,
        "prices": prices,
        "raw_site_result": payload,
    }


async def _run(output_path: Path, timeout_seconds: float) -> int:
    summaries: list[dict[str, Any]] = []

    try:
        for case in DEFAULT_CASES:
            scraper = None
            is_archived = False
            try:
                scraper, is_archived = await _get_demo_scraper(case["site"])
                result = await asyncio.wait_for(
                    scraper.scrape_sku(case["sku"], case["brand"]),
                    timeout=timeout_seconds,
                )
            except TimeoutError:
                summaries.append(
                    {
                        "case_id": case["id"],
                        "site": case["site"].value,
                        "sku": case["sku"],
                        "brand": case["brand"],
                        "job_id": None,
                        "job_status": "timeout",
                        "site_status": "timeout",
                        "error_message": f"Timed out after {timeout_seconds} seconds.",
                        "search_time_ms": 0,
                        "total_results": 0,
                        "best_price": None,
                        "prices": [],
                        "raw_site_result": None,
                    }
                )
            except Exception as exc:
                summaries.append(
                    {
                        "case_id": case["id"],
                        "site": case["site"].value,
                        "sku": case["sku"],
                        "brand": case["brand"],
                        "job_id": None,
                        "job_status": "error",
                        "site_status": "error",
                        "error_message": str(exc),
                        "search_time_ms": 0,
                        "total_results": 0,
                        "best_price": None,
                        "prices": [],
                        "raw_site_result": None,
                    }
                )
            else:
                summaries.append(_summarize_site_result(case, result))
            finally:
                if is_archived and scraper is not None:
                    await scraper.shutdown()
    finally:
        output = {
            "generated_at": datetime.now(UTC).isoformat(),
            "purpose": "local scraper demo raw results",
            "cases": summaries,
        }
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
        print(json.dumps(output, indent=2, ensure_ascii=False))

        try:
            await asyncio.wait_for(shutdown_all_scrapers(), timeout=30)
        except TimeoutError:
            print("warning: timed out while shutting down one or more scraper browser contexts")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        default="docs/validation/latest_scraper_demo_results.json",
        help="Where to write the captured JSON.",
    )
    parser.add_argument("--timeout-seconds", type=float, default=180.0)
    args = parser.parse_args()
    return asyncio.run(_run(Path(args.output), args.timeout_seconds))


if __name__ == "__main__":
    raise SystemExit(main())
