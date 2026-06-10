#!/usr/bin/env python3
"""Run one SKU per site through Playwright with proxy settings from the environment.

Use after proxy_readiness_check.py passes. Does not call supplier APIs except via
the browser. Archived sites (goparts, procurapecas, ebay) are included when
listed in --sites or the default rollout set.

Examples:
  PROXY_ROTATION_ENABLED=true PROXY_URLS='["http://user:pass@host:12323"]' \\
    uv run python scripts/proxy_site_smoke.py --from-env

  uv run python scripts/proxy_site_smoke.py --site melibox --sku 51766536
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import settings  # noqa: E402
from src.models.schemas import SiteId, SiteResult  # noqa: E402
from src.scrapers import (  # noqa: E402
    ARCHIVED_SCRAPER_REGISTRY,
    SCRAPER_REGISTRY,
    get_scraper,
    shutdown_all_scrapers,
)
from src.utils.proxy_manager import get_proxy_manager, reset_proxy_manager  # noqa: E402

SITE_CHOICES = (
    "gm",
    "ml",
    "vw",
    "eu",
    "pecadireta",
    "melibox",
    "goparts",
    "procurapecas",
    "ebay",
)

# Canonical rollout SKUs — see docs/SPECS/PROXY_ROTATION_SPEC.md
DEFAULT_ROLLOUT_CASES: tuple[tuple[str, str, str], ...] = (
    ("melibox", "51766536", ""),
    ("pecadireta", "06K907811B", ""),
    ("gm", "22781768", "GM"),
    ("vw", "5U6867287Y20", "VW"),
    ("eu", "06K907811B", "VW"),
    ("ml", "51766536", ""),
    ("goparts", "06K907811B", ""),
    ("procurapecas", "06K907811B", ""),
    ("ebay", "51766536", ""),
)


@dataclass
class SmokeOutcome:
    site: str
    sku: str
    brand: str
    status: str
    exact_results: int
    priced_results: int
    error_message: str
    search_time_ms: int
    proxy_rotation_enabled: bool
    proxy_configured: bool


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sites",
        nargs="+",
        choices=SITE_CHOICES,
        help="Sites to smoke (default: melibox + active regression set).",
    )
    parser.add_argument("--site", choices=SITE_CHOICES, help="Single site override.")
    parser.add_argument("--sku", help="SKU when using --site.")
    parser.add_argument("--brand", default="", help="Brand when using --site.")
    parser.add_argument(
        "--from-env",
        action="store_true",
        help="Require PROXY_ROTATION_ENABLED and non-empty PROXY_URLS.",
    )
    parser.add_argument(
        "--include-archived",
        action="store_true",
        help="Add goparts and procurapecas to the default site list.",
    )
    parser.add_argument("--timeout-seconds", type=float, default=180.0)
    parser.add_argument(
        "--output",
        default="docs/validation/latest_proxy_site_smoke.json",
        help="JSON report path.",
    )
    parser.add_argument("--json", action="store_true", help="Print JSON to stdout only.")
    return parser.parse_args()


def _cases_from_args(args: argparse.Namespace) -> list[tuple[str, str, str]]:
    if args.site:
        if not args.sku:
            raise SystemExit("--sku is required when --site is set.")
        return [(args.site, args.sku, args.brand)]

    if args.sites:
        site_set = set(args.sites)
        return [case for case in DEFAULT_ROLLOUT_CASES if case[0] in site_set]

    sites = {"melibox", "pecadireta", "gm", "vw", "eu", "ml"}
    if args.include_archived:
        sites.update({"goparts", "procurapecas", "ebay"})
    return [case for case in DEFAULT_ROLLOUT_CASES if case[0] in sites]


def _validate_proxy_env(args: argparse.Namespace) -> None:
    if not args.from_env:
        return
    if not settings.proxy_rotation_enabled:
        raise SystemExit("PROXY_ROTATION_ENABLED must be true when using --from-env.")
    if not settings.proxy_urls:
        raise SystemExit("PROXY_URLS must be set when using --from-env.")


async def _scrape_case(
    site: str,
    sku: str,
    brand: str,
    timeout_seconds: float,
) -> SmokeOutcome:
    site_id = SiteId(site)
    proxy_manager = get_proxy_manager()
    proxy_manager.begin_sku(sku, brand)
    archived_scraper = None
    try:
        if site_id in SCRAPER_REGISTRY:
            scraper = await get_scraper(site_id)
        elif site_id in ARCHIVED_SCRAPER_REGISTRY:
            scraper = ARCHIVED_SCRAPER_REGISTRY[site_id]()
            archived_scraper = scraper
        else:
            raise ValueError(f"No scraper for site: {site}")

        result: SiteResult = await asyncio.wait_for(
            scraper.scrape_sku(sku, brand),
            timeout=timeout_seconds,
        )
        payload = result.model_dump(mode="json")
        parts = payload.get("results") or []
        priced = [
            p
            for p in parts
            if isinstance(p.get("price"), int | float) and p.get("price", 0) > 0
        ]
        exact = sum(1 for p in parts if p.get("exact_match") is True)
        return SmokeOutcome(
            site=site,
            sku=sku,
            brand=brand,
            status=str(payload.get("status", "error")),
            exact_results=exact,
            priced_results=len(priced),
            error_message=str(payload.get("error_message") or ""),
            search_time_ms=int(payload.get("search_time_ms") or 0),
            proxy_rotation_enabled=settings.proxy_rotation_enabled,
            proxy_configured=bool(settings.proxy_urls),
        )
    finally:
        if archived_scraper is not None:
            await archived_scraper.shutdown()
        proxy_manager.clear_sku()


async def _run(args: argparse.Namespace) -> int:
    _validate_proxy_env(args)
    os.environ.setdefault("MOCK_SCRAPERS", "false")
    os.environ.setdefault("PLAYWRIGHT_HEADLESS", "true")

    cases = _cases_from_args(args)
    if not cases:
        raise SystemExit("No smoke cases selected.")

    outcomes: list[SmokeOutcome] = []
    for site, sku, brand in cases:
        outcomes.append(
            await _scrape_case(site, sku, brand, args.timeout_seconds),
        )

    await shutdown_all_scrapers()
    reset_proxy_manager()

    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "proxy_rotation_enabled": settings.proxy_rotation_enabled,
        "proxy_url_count": len(settings.proxy_urls),
        "cases": [asdict(o) for o in outcomes],
    }
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"Wrote {output_path}")
        for outcome in outcomes:
            mark = "PASS" if outcome.status == "success" else outcome.status.upper()
            print(
                f"  {outcome.site:14} {mark:10} "
                f"exact={outcome.exact_results} priced={outcome.priced_results} "
                f"ms={outcome.search_time_ms}",
            )
            if outcome.error_message:
                print(f"    error: {outcome.error_message[:120]}")

    blocked = sum(1 for o in outcomes if o.status == "blocked")
    failed = sum(1 for o in outcomes if o.status in {"error", "timeout"})
    return 1 if blocked or failed else 0


def main() -> int:
    args = _parse_args()
    return asyncio.run(_run(args))


if __name__ == "__main__":
    raise SystemExit(main())
