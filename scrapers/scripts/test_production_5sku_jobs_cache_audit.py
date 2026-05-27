#!/usr/bin/env python3
"""Production audit: 5 SKUs via POST /jobs + poll (n8n path), live then cached."""

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

OUTPUT_PATH = ROOT / "docs/validation/latest_production_5sku_jobs_cache_audit.json"
CALLBACK_BASE = (
    "https://automacao.tktechnologies.com.br/webhook/scraper-result"
    "?source=cache-test&notify=none"
)

from production_sku_pool import FULL_POOL, resolve_seed, sample_cases  # noqa: E402

POLL_TIMEOUT_S = 180
POLL_INTERVAL_S = 3


@dataclass
class JobRun:
    label: str
    job_id: str = ""
    submit_status: int = 0
    submit_error: str = ""
    poll_status: str = ""
    elapsed_ms: int = 0
    payload: dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return bool(self.job_id) and self.poll_status in (
            "completed",
            "partial",
            "failed",
        )

    def sku_summary(self) -> dict[str, Any]:
        results = self.payload.get("results") or []
        if not results:
            return {}
        r0 = results[0] if isinstance(results[0], dict) else {}
        sites = []
        for sr in r0.get("site_results") or []:
            if not isinstance(sr, dict):
                continue
            sites.append(
                {
                    "site": sr.get("site"),
                    "status": sr.get("status"),
                    "from_cache": sr.get("from_cache"),
                    "search_time_ms": sr.get("search_time_ms"),
                }
            )
        bp = r0.get("best_price")
        return {
            "cache_hits": r0.get("cache_hits"),
            "live_scrapes": r0.get("live_scrapes"),
            "best_price": (
                {
                    "price": bp.get("price"),
                    "currency": bp.get("currency"),
                    "exact_match": bp.get("exact_match"),
                }
                if isinstance(bp, dict)
                else None
            ),
            "sites": sites,
        }


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


def _http_json(
    url: str,
    *,
    api_key: str,
    method: str = "GET",
    body: dict[str, Any] | None = None,
    timeout: float = 60.0,
) -> tuple[int, dict[str, Any], str]:
    data = json.dumps(body).encode() if body is not None else None
    req = Request(
        url,
        data=data,
        headers={"X-API-Key": api_key, "Content-Type": "application/json"},
        method=method,
    )
    try:
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            try:
                return resp.status, json.loads(raw), ""
            except json.JSONDecodeError as exc:
                return resp.status, {}, f"invalid json: {exc}"
    except HTTPError as exc:
        try:
            payload = json.loads(exc.read())
        except Exception:
            payload = {"detail": exc.reason}
        return exc.code, payload, str(payload.get("detail", exc.reason))
    except Exception as exc:
        return 0, {}, str(exc)


def submit_job(
    api_base: str,
    api_key: str,
    *,
    sku: str,
    brand: str,
    sites: list[str],
    force_refresh: bool,
    with_callback: bool,
) -> JobRun:
    body: dict[str, Any] = {
        "items": [{"sku": sku, "brand": brand}],
        "sites": sites,
        "force_refresh": force_refresh,
        "priority": 5,
    }
    if with_callback:
        body["callback_url"] = CALLBACK_BASE

    status, payload, err = _http_json(
        f"{api_base}/jobs",
        api_key=api_key,
        method="POST",
        body=body,
        timeout=30.0,
    )
    run = JobRun(
        label="submit",
        submit_status=status,
        submit_error=err,
        payload=payload,
    )
    if status == 200 and isinstance(payload, dict):
        run.job_id = str(payload.get("job_id", ""))
    return run


def poll_job(api_base: str, api_key: str, job_id: str) -> JobRun:
    t0 = time.perf_counter()
    deadline = t0 + POLL_TIMEOUT_S
    last: dict[str, Any] = {}
    poll_status = ""
    while time.perf_counter() < deadline:
        status, payload, err = _http_json(
            f"{api_base}/jobs/{job_id}",
            api_key=api_key,
            timeout=30.0,
        )
        if status != 200:
            return JobRun(
                label="poll",
                job_id=job_id,
                submit_status=status,
                submit_error=err,
                elapsed_ms=int((time.perf_counter() - t0) * 1000),
                payload=payload,
            )
        last = payload
        poll_status = str(payload.get("status", ""))
        if poll_status in ("completed", "partial", "failed"):
            break
        time.sleep(POLL_INTERVAL_S)

    return JobRun(
        label="poll",
        job_id=job_id,
        poll_status=poll_status,
        elapsed_ms=int((time.perf_counter() - t0) * 1000),
        payload=last,
    )


def audit_cache_pair(first: JobRun, second: JobRun) -> dict[str, Any]:
    issues: list[str] = []
    if not first.job_id or not first.poll_status:
        issues.append(f"first_job_incomplete: {first.submit_error or first.poll_status}")
    if not second.job_id or not second.poll_status:
        issues.append(f"second_job_incomplete: {second.submit_error or second.poll_status}")

    s1, s2 = first.sku_summary(), second.sku_summary()
    if first.job_id and second.job_id:
        if (s2.get("cache_hits") or 0) < 1:
            issues.append(f"cache_hits_expected_ge_1 got={s2.get('cache_hits')}")
        if s2.get("live_scrapes") != 0:
            issues.append(f"live_scrapes_expected_0 got={s2.get('live_scrapes')}")
        if not any(site.get("from_cache") for site in (s2.get("sites") or [])):
            issues.append("from_cache_false_on_second_job")

    return {
        "pass": len(issues) == 0 and first.ok and second.ok,
        "issues": issues,
        "first_ms": first.elapsed_ms,
        "second_ms": second.elapsed_ms,
        "first": s1,
        "second": s2,
    }


def audit_contract(job: JobRun) -> dict[str, Any]:
    issues: list[str] = []
    results = job.payload.get("results") or []
    if not results:
        return {"pass": False, "issues": ["no_results"]}

    r0 = results[0]
    for sr in r0.get("site_results") or []:
        status = sr.get("status")
        if status == "success" and not (sr.get("results") or []):
            issues.append(f"success_without_results:{sr.get('site')}")
        for part in sr.get("results") or []:
            price = part.get("price")
            exact = part.get("exact_match")
            if price and price > 0 and not exact:
                issues.append(f"priced_non_exact:{sr.get('site')}")

    bp = r0.get("best_price")
    if isinstance(bp, dict) and bp.get("price"):
        if not bp.get("exact_match"):
            issues.append("best_price_not_exact_match")
        cur = bp.get("currency")
        for sr in r0.get("site_results") or []:
            for part in sr.get("results") or []:
                if (
                    part.get("exact_match")
                    and part.get("price")
                    and part.get("currency") != cur
                ):
                    issues.append("best_price_mixed_currency_risk")
                    break

    return {"pass": len(issues) == 0, "issues": issues}


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="5-SKU /jobs cache audit (random pool sample)")
    parser.add_argument("--seed", type=int, default=None, help="RNG seed (or PRODUCTION_TEST_SKU_SEED)")
    args = parser.parse_args()

    cases = sample_cases(5, seed=args.seed)
    seed_used = resolve_seed(args.seed)

    api_base, api_key = _resolve_api()
    print(f"API: {api_base}")
    print(f"Callback: {CALLBACK_BASE}")
    print(f"Pool: {len(FULL_POOL)} SKUs — sample seed={seed_used}")
    for c in cases:
        print(f"  - {c['sku']} brand={c['brand']!r} sites={c['sites']}")

    report: dict[str, Any] = {
        "generated_at": datetime.now(UTC).isoformat(),
        "api_base": api_base,
        "callback_url": CALLBACK_BASE,
        "pool_size": len(FULL_POOL),
        "sample_seed": seed_used,
        "sampled_cases": cases,
        "cases": [],
        "e2e_job_ids": [],
        "summary": {},
    }

    passed = 0
    e2e_cases = cases[:3]

    for case in cases:
        case_id = case["id"]
        print(f"\n=== {case_id} ===")

        j1_submit = submit_job(
            api_base,
            api_key,
            sku=case["sku"],
            brand=case["brand"],
            sites=case["sites"],
            force_refresh=False,
            with_callback=case in e2e_cases,
        )
        if not j1_submit.job_id:
            print(f"  submit1 FAIL: {j1_submit.submit_error} {j1_submit.payload}")
            report["cases"].append({"id": case_id, "error": "submit1_failed"})
            continue

        j1 = poll_job(api_base, api_key, j1_submit.job_id)
        j1.label = f"{case_id}-job1"
        print(
            f"  job1: {j1.job_id} status={j1.poll_status} ms={j1.elapsed_ms} "
            f"summary={j1.sku_summary()}"
        )

        j2_submit = submit_job(
            api_base,
            api_key,
            sku=case["sku"],
            brand=case["brand"],
            sites=case["sites"],
            force_refresh=False,
            with_callback=False,
        )
        j2 = poll_job(api_base, api_key, j2_submit.job_id)
        j2.label = f"{case_id}-job2"
        print(
            f"  job2: {j2.job_id} status={j2.poll_status} ms={j2.elapsed_ms} "
            f"summary={j2.sku_summary()}"
        )

        cache_audit = audit_cache_pair(j1, j2)
        contract = audit_contract(j1)
        if cache_audit["pass"]:
            passed += 1
            print("  CACHE: PASS")
        else:
            print(f"  CACHE: FAIL — {cache_audit['issues']}")

        entry = {
            "id": case_id,
            "sku": case["sku"],
            "brand": case["brand"],
            "sites": case["sites"],
            "job1_id": j1.job_id,
            "job2_id": j2.job_id,
            "cache_audit": cache_audit,
            "contract_audit": contract,
            "with_callback": case in e2e_cases,
        }
        report["cases"].append(entry)
        if case in e2e_cases:
            report["e2e_job_ids"].append(j1.job_id)

    total = len(cases)
    report["summary"] = {
        "total": total,
        "cache_pass": passed,
        "cache_fail": total - passed,
        "overall_pass": passed >= 4,
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nWrote {OUTPUT_PATH}")
    print(f"SUMMARY: {passed}/{total} cache pairs PASS (threshold >=4)")
    return 0 if passed >= 4 else 1


if __name__ == "__main__":
    sys.exit(main())
