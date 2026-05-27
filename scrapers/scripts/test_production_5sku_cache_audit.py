#!/usr/bin/env python3
"""Production audit: 5 SKUs via /lookup curl path, live then cache hit."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

OUTPUT_PATH = ROOT / "docs/validation/latest_production_5sku_cache_audit.json"

from production_sku_pool import FULL_POOL, resolve_seed, sample_cases  # noqa: E402


@dataclass
class LookupResult:
    label: str
    force_refresh: bool
    http_status: int
    elapsed_ms: int
    error: str = ""
    payload: dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.http_status == 200 and not self.error

    def site_summary(self) -> list[dict[str, Any]]:
        out = []
        for sr in self.payload.get("site_results") or []:
            if not isinstance(sr, dict):
                continue
            out.append(
                {
                    "site": sr.get("site"),
                    "status": sr.get("status"),
                    "from_cache": sr.get("from_cache"),
                    "cached_at": sr.get("cached_at"),
                    "search_time_ms": sr.get("search_time_ms"),
                    "has_price": any(
                        isinstance(p.get("price"), (int, float)) and float(p.get("price")) > 0
                        for p in (sr.get("results") or [])
                    ),
                }
            )
        return out


def _resolve_api() -> tuple[str, str]:
    api_base = os.environ.get("API_BASE", "").strip()
    api_key = os.environ.get("API_KEY", "").strip()
    if api_base and api_key:
        return api_base.rstrip("/"), api_key

    fqdn = subprocess.check_output(
        [
            "az",
            "containerapp",
            "show",
            "-g",
            "automation",
            "-n",
            "cdp-scrapers-api-prod",
            "--query",
            "properties.configuration.ingress.fqdn",
            "-o",
            "tsv",
        ],
        text=True,
    ).strip().strip("\r\n")
    api_key = subprocess.check_output(
        [
            "az",
            "keyvault",
            "secret",
            "show",
            "--vault-name",
            "cdp-scrapers-kv-prod",
            "--name",
            "api-key",
            "--query",
            "value",
            "-o",
            "tsv",
        ],
        text=True,
    ).strip().strip("\r\n")
    return f"https://{fqdn}/api/v1", api_key


def lookup(
    api_base: str,
    api_key: str,
    *,
    sku: str,
    brand: str,
    sites: list[str],
    force_refresh: bool,
    label: str,
    timeout: float = 180.0,
) -> LookupResult:
    body = json.dumps(
        {
            "sku": sku,
            "brand": brand,
            "sites": sites,
            "force_refresh": force_refresh,
        }
    ).encode()
    req = Request(
        f"{api_base}/lookup",
        data=body,
        headers={"X-API-Key": api_key, "Content-Type": "application/json"},
        method="POST",
    )
    t0 = time.perf_counter()
    try:
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            elapsed_ms = int((time.perf_counter() - t0) * 1000)
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError as exc:
                return LookupResult(
                    label=label,
                    force_refresh=force_refresh,
                    http_status=resp.status,
                    elapsed_ms=elapsed_ms,
                    error=f"invalid json: {exc}",
                )
            return LookupResult(
                label=label,
                force_refresh=force_refresh,
                http_status=resp.status,
                elapsed_ms=elapsed_ms,
                payload=payload,
            )
    except HTTPError as exc:
        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        try:
            payload = json.loads(exc.read())
        except Exception:
            payload = {"detail": exc.reason}
        return LookupResult(
            label=label,
            force_refresh=force_refresh,
            http_status=exc.code,
            elapsed_ms=elapsed_ms,
            error=str(payload.get("detail", exc.reason)),
            payload=payload,
        )
    except Exception as exc:
        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        return LookupResult(
            label=label,
            force_refresh=force_refresh,
            http_status=0,
            elapsed_ms=elapsed_ms,
            error=str(exc),
        )


def audit_cache_pair(live: LookupResult, cached: LookupResult) -> dict[str, Any]:
    issues: list[str] = []
    if not live.ok:
        issues.append(f"live_failed: {live.error or live.http_status}")
    if not cached.ok:
        issues.append(f"cached_failed: {cached.error or cached.http_status}")

    cache_hits = cached.payload.get("cache_hits")
    live_scrapes = cached.payload.get("live_scrapes")
    sites = cached.site_summary()

    if live.ok and cached.ok:
        if cache_hits is None:
            issues.append("missing_cache_hits_field")
        elif cache_hits < 1:
            issues.append(f"cache_hits_expected_ge_1 got={cache_hits}")
        if live_scrapes is None:
            issues.append("missing_live_scrapes_field")
        elif live_scrapes != 0:
            issues.append(f"cached_live_scrapes_expected_0 got={live_scrapes}")
        if not any(s.get("from_cache") for s in sites):
            issues.append("from_cache_false_on_cached_call")
        # Cached /lookup should be well under live scrape latency (API direct path).
        if cached.elapsed_ms > 5000:
            issues.append(f"cached_wall_ms_too_high got={cached.elapsed_ms}")
        for s in sites:
            if s.get("from_cache") and (s.get("search_time_ms") or 0) > 500:
                issues.append(
                    f"cached_search_time_ms_should_be_near_zero got={s.get('search_time_ms')}"
                )

    return {
        "pass": len(issues) == 0 and live.ok and cached.ok,
        "issues": issues,
        "live_ms": live.elapsed_ms,
        "cached_ms": cached.elapsed_ms,
        "live": {
            "cache_hits": live.payload.get("cache_hits"),
            "live_scrapes": live.payload.get("live_scrapes"),
            "sites": live.site_summary(),
        },
        "cached": {
            "cache_hits": cache_hits,
            "live_scrapes": live_scrapes,
            "sites": sites,
        },
    }


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="5-SKU /lookup cache audit (random pool sample)")
    parser.add_argument("--seed", type=int, default=None, help="RNG seed (or PRODUCTION_TEST_SKU_SEED)")
    args = parser.parse_args()

    cases = sample_cases(5, seed=args.seed)
    seed_used = resolve_seed(args.seed)

    api_base, api_key = _resolve_api()
    print(f"API: {api_base}")
    print(f"Pool: {len(FULL_POOL)} SKUs — sample seed={seed_used}")
    for c in cases:
        print(f"  - {c['sku']} brand={c['brand']!r} sites={c['sites']}")
    health_req = Request(f"{api_base}/health")
    with urlopen(health_req, timeout=30) as resp:
        health = json.loads(resp.read())
    print(f"health: {health.get('status')}")

    report: dict[str, Any] = {
        "generated_at": datetime.now(UTC).isoformat(),
        "api_base": api_base,
        "pool_size": len(FULL_POOL),
        "sample_seed": seed_used,
        "sampled_cases": cases,
        "image": subprocess.check_output(
            [
                "az",
                "containerapp",
                "show",
                "-g",
                "automation",
                "-n",
                "cdp-scrapers-api-prod",
                "--query",
                "properties.template.containers[0].image",
                "-o",
                "tsv",
            ],
            text=True,
        ).strip(),
        "cases": [],
        "summary": {},
    }

    passed = 0
    for case in cases:
        case_id = case["id"]
        print(f"\n=== {case_id} sku={case['sku']} sites={case['sites']} ===")
        live = lookup(
            api_base,
            api_key,
            sku=case["sku"],
            brand=case["brand"],
            sites=case["sites"],
            force_refresh=True,
            label=f"{case_id}-live",
        )
        print(
            f"  live: http={live.http_status} ms={live.elapsed_ms} "
            f"hits={live.payload.get('cache_hits')} live_scrapes={live.payload.get('live_scrapes')}"
        )
        for s in live.site_summary():
            print(f"    {s['site']}: {s['status']} price={s['has_price']}")

        cached = lookup(
            api_base,
            api_key,
            sku=case["sku"],
            brand=case["brand"],
            sites=case["sites"],
            force_refresh=False,
            label=f"{case_id}-cached",
        )
        print(
            f"  cached: http={cached.http_status} ms={cached.elapsed_ms} "
            f"hits={cached.payload.get('cache_hits')} live_scrapes={cached.payload.get('live_scrapes')}"
        )
        for s in cached.site_summary():
            print(f"    {s['site']}: {s['status']} from_cache={s['from_cache']}")

        audit = audit_cache_pair(live, cached)
        if audit["pass"]:
            passed += 1
            print("  CACHE AUDIT: PASS")
        else:
            print(f"  CACHE AUDIT: FAIL — {audit['issues']}")

        report["cases"].append(
            {
                "id": case_id,
                "sku": case["sku"],
                "brand": case["brand"],
                "sites": case["sites"],
                "audit": audit,
                "live_response": live.payload if live.ok else {"error": live.error, "detail": live.payload},
                "cached_response": cached.payload if cached.ok else {"error": cached.error, "detail": cached.payload},
            }
        )

    total = len(cases)
    report["summary"] = {
        "total": total,
        "cache_pass": passed,
        "cache_fail": total - passed,
        "overall_pass": passed == total,
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nWrote {OUTPUT_PATH}")
    print(f"SUMMARY: {passed}/{total} cache pairs PASS")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
