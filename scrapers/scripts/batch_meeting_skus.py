"""Batch scrape meeting SKUs across all active scraper sites (localhost)."""

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
from src.scrapers import SCRAPER_REGISTRY, get_scraper, shutdown_all_scrapers
from src.services.result_formatter import _find_best_price

MEETING_SKUS = [
    "60910T14M00ZZ",
    "661003M6M00ZZ",
    "621003M6M00ZZ",
    "767203M6M01",
    "846403M6M01ZA",
    "793251Y000",
    "53486204",
    "84035768",
    "8.77E+15",
    "52274186",
    "51789373",
    "52063874",
    "631008317R",
    "52200024",
    "K8EP17LR0A",
    "868857LR8A",
    "868847LR8A",
    "D3BB/ 15B200/AA/5UA",
    "C1BB/ 15A222/DA/5YZ",
    "04601T7TM00ZZ",
]

SITE_LABELS = {
    SiteId.GM: "GM (Peça Chevrolet)",
    SiteId.MERCADO_LIVRE: "Mercado Livre",
    SiteId.VW: "VW Oficial",
    SiteId.EUROPE: "EU Imports",
    SiteId.PECA_DIRETA: "Peça Direta",
    SiteId.MELIBOX: "Melibox/Sellerbox",
}


def _summarize(sku: str, site_id: SiteId, site_result: SiteResult | None, *, error: str = "") -> dict[str, Any]:
    if site_result is None:
        return {
            "sku": sku,
            "site": site_id.value,
            "site_name": SITE_LABELS.get(site_id, site_id.value),
            "status": "error" if error else "timeout",
            "error_message": error,
            "search_time_ms": 0,
            "has_price": False,
            "price": None,
            "currency": None,
            "availability": None,
            "exact_match": False,
            "sku_found": None,
            "total_results": 0,
            "product_url": None,
            "title": None,
        }

    payload = site_result.model_dump(mode="json")
    parts = payload.get("results", [])
    best = _find_best_price(site_result.results)
    priced = [
        p for p in parts
        if isinstance(p.get("price"), int | float) and float(p.get("price")) > 0
    ]
    first_exact = next((p for p in parts if p.get("exact_match")), None)
    pick = best or (priced[0] if priced else first_exact)

    price = pick.price if pick else None
    return {
        "sku": sku,
        "site": site_id.value,
        "site_name": SITE_LABELS.get(site_id, site_id.value),
        "status": payload.get("status", "unknown"),
        "error_message": payload.get("error_message", ""),
        "search_time_ms": payload.get("search_time_ms", 0),
        "has_price": price is not None and float(price) > 0,
        "price": float(price) if price is not None else None,
        "currency": pick.currency.value if pick and hasattr(pick.currency, "value") else (pick.currency if pick else None),
        "availability": pick.availability if pick else None,
        "exact_match": pick.exact_match if pick else False,
        "sku_found": pick.sku_found if pick else None,
        "total_results": len(parts),
        "product_url": pick.product_url if pick else None,
        "title": (pick.raw_title[:80] + "…") if pick and len(pick.raw_title) > 80 else (pick.raw_title if pick else None),
        "all_prices": [
            {
                "price": p.get("price"),
                "currency": p.get("currency"),
                "exact_match": p.get("exact_match"),
                "availability": p.get("availability"),
                "sku_found": p.get("sku_found"),
            }
            for p in parts
        ],
    }


async def _run(output_path: Path, timeout_seconds: float, skus: list[str]) -> int:
    sites = list(SCRAPER_REGISTRY.keys())
    rows: list[dict[str, Any]] = []
    total = len(skus) * len(sites)
    done = 0

    try:
        for site_id in sites:
            scraper = await get_scraper(site_id)
            for sku in skus:
                done += 1
                label = f"[{done}/{total}] {site_id.value} × {sku}"
                print(label, flush=True)
                try:
                    result = await asyncio.wait_for(
                        scraper.scrape_sku(sku.strip(), brand=""),
                        timeout=timeout_seconds,
                    )
                    row = _summarize(sku, site_id, result)
                except TimeoutError:
                    row = _summarize(sku, site_id, None, error=f"Timed out after {timeout_seconds}s")
                    row["status"] = "timeout"
                except Exception as exc:
                    row = _summarize(sku, site_id, None, error=str(exc))
                    row["status"] = "error"
                rows.append(row)
                print(f"  -> {row['status']}", flush=True)
    finally:
        try:
            await asyncio.wait_for(shutdown_all_scrapers(), timeout=60)
        except TimeoutError:
            print("warning: scraper shutdown timed out", flush=True)

    output = {
        "generated_at": datetime.now(UTC).isoformat(),
        "purpose": "meeting SKU batch — all active sites localhost",
        "skus": skus,
        "sites": [s.value for s in sites],
        "total_cases": total,
        "results": rows,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nWrote {output_path}", flush=True)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        default="docs/validation/meeting_sku_batch_results.json",
    )
    parser.add_argument("--timeout-seconds", type=float, default=120.0)
    args = parser.parse_args()
    return asyncio.run(_run(Path(args.output), args.timeout_seconds, MEETING_SKUS))


if __name__ == "__main__":
    raise SystemExit(main())
