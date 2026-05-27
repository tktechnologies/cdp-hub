"""Validate real local scraper runs against a manually verified manifest."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

TERMINAL_STATUSES = {"completed", "partial", "failed"}
PLACEHOLDER_RE = re.compile(r"REPLACE_|YOUR_|CHANGE_ME|TODO", re.IGNORECASE)


@dataclass(frozen=True)
class ValidationCase:
    id: str
    site: str
    sku: str
    brand: str
    expect_result: bool
    expected_currency: str
    expected_condition: str
    expected_price_min: float | None
    expected_price_max: float | None
    evidence_url: str


def _fail(message: str) -> None:
    raise RuntimeError(message)


def _normalize_sku(sku: str) -> str:
    return re.sub(r"[\s\-\.\/]", "", sku.strip()).upper()


def _load_manifest(path: Path) -> list[ValidationCase]:
    if not path.exists():
        _fail(f"Manifest not found: {path}")

    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("require_real_scrapers") is not True:
        _fail("Manifest must set require_real_scrapers=true for this validation.")

    raw_cases = data.get("cases")
    if not isinstance(raw_cases, list) or not raw_cases:
        _fail("Manifest must contain a non-empty cases list.")

    cases: list[ValidationCase] = []
    seen_sites: set[str] = set()
    for raw in raw_cases:
        if not isinstance(raw, dict):
            _fail("Every manifest case must be an object.")
        serialized = json.dumps(raw)
        if PLACEHOLDER_RE.search(serialized):
            _fail(f"Manifest case {raw.get('id', '<missing>')} still contains placeholders.")

        case = ValidationCase(
            id=str(raw["id"]),
            site=str(raw["site"]),
            sku=str(raw["sku"]),
            brand=str(raw.get("brand", "")),
            expect_result=bool(raw["expect_result"]),
            expected_currency=str(raw["expected_currency"]),
            expected_condition=str(raw.get("expected_condition", "unknown")),
            expected_price_min=raw.get("expected_price_min"),
            expected_price_max=raw.get("expected_price_max"),
            evidence_url=str(raw.get("evidence_url", "")),
        )
        if case.expect_result and (case.expected_price_min is None or case.expected_price_max is None):
            _fail(f"Case {case.id} expects a result but has no price range.")
        if case.expect_result and not case.evidence_url:
            _fail(f"Case {case.id} expects a result but has no evidence_url.")
        cases.append(case)
        seen_sites.add(case.site)

    required_sites = {
        "gm",
        "ml",
        "vw",
        "eu",
        "pecadireta",
        "melibox",
    }
    missing = sorted(required_sites - seen_sites)
    if missing:
        _fail(f"Manifest is missing required real scraper sites: {', '.join(missing)}")

    return cases


def _credential_gate(cases: list[ValidationCase]) -> None:
    if os.environ.get("MOCK_SCRAPERS", "").lower() in {"1", "true", "yes"}:
        _fail("MOCK_SCRAPERS must be false or unset for real scraper validation.")
    if os.environ.get("PROXY_ROTATION_ENABLED", "").lower() in {"1", "true", "yes"}:
        _fail("PROXY_ROTATION_ENABLED must be false for local validation.")

    # GM is a public scraper. MockGMScraper is only enabled explicitly through
    # MOCK_SCRAPERS=true, which is already blocked above.


async def _submit_job(client: httpx.AsyncClient, api_key: str, case: ValidationCase) -> str:
    response = await client.post(
        "/api/v1/jobs",
        headers={"X-API-Key": api_key},
        json={"items": [{"sku": case.sku, "brand": case.brand}], "sites": [case.site]},
    )
    response.raise_for_status()
    return str(response.json()["job_id"])


async def _wait_for_job(
    client: httpx.AsyncClient,
    api_key: str,
    job_id: str,
    timeout_seconds: float,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        response = await client.get(f"/api/v1/jobs/{job_id}", headers={"X-API-Key": api_key})
        response.raise_for_status()
        data = response.json()
        if data["status"] in TERMINAL_STATUSES:
            return data
        await asyncio.sleep(2)
    _fail(f"Timed out waiting for job {job_id}")


def _find_parts(job: dict[str, Any], case: ValidationCase) -> list[dict[str, Any]]:
    parts: list[dict[str, Any]] = []
    for sku_result in job.get("results", []):
        if sku_result.get("sku") != case.sku:
            continue
        for site_result in sku_result.get("site_results", []):
            if site_result.get("site") == case.site:
                parts.extend(site_result.get("results", []))
    return parts


def _validate_api_result(job: dict[str, Any], case: ValidationCase) -> None:
    parts = _find_parts(job, case)
    if not case.expect_result:
        if parts:
            _fail(f"Case {case.id} expected no results but got {len(parts)}.")
        return

    if not parts:
        _fail(f"Case {case.id} expected at least one result.")

    normalized_search = _normalize_sku(case.sku)
    matching_parts = [
        part for part in parts
        if part.get("exact_match") is True
        and _normalize_sku(str(part.get("sku_found", ""))) == normalized_search
    ]
    if not matching_parts:
        _fail(f"Case {case.id} has no exact SKU match for {case.sku}.")

    for part in matching_parts:
        price = part.get("price")
        if not isinstance(price, int | float) or price <= 0:
            _fail(f"Case {case.id} returned invalid price: {price}")
        if price < case.expected_price_min or price > case.expected_price_max:  # type: ignore[operator]
            _fail(
                f"Case {case.id} price {price} outside expected range "
                f"{case.expected_price_min}-{case.expected_price_max}."
            )
        if part.get("currency") != case.expected_currency:
            _fail(f"Case {case.id} currency mismatch: {part.get('currency')}")
        if case.expected_condition != "unknown" and part.get("condition") != case.expected_condition:
            _fail(f"Case {case.id} condition mismatch: {part.get('condition')}")

    for sku_result in job.get("results", []):
        best_price = sku_result.get("best_price")
        priced_currencies = {
            part.get("currency")
            for site_result in sku_result.get("site_results", [])
            for part in site_result.get("results", [])
            if part.get("exact_match") and part.get("price")
        }
        if len(priced_currencies) > 1 and best_price is not None:
            _fail(f"Case {case.id} selected best_price across mixed currencies.")


async def _validate_database(database_url: str, job_id: str, case: ValidationCase) -> None:
    engine = create_async_engine(database_url)
    try:
        async with engine.begin() as conn:
            job_row = (
                await conn.execute(
                    text("select id, status, total_items from scrape_jobs where id = :job_id"),
                    {"job_id": job_id},
                )
            ).mappings().first()
            if not job_row:
                _fail(f"Job {job_id} was not persisted.")

            item_row = (
                await conn.execute(
                    text("select id, status from scrape_items where job_id = :job_id and sku = :sku"),
                    {"job_id": job_id, "sku": case.sku},
                )
            ).mappings().first()
            if not item_row:
                _fail(f"Case {case.id} item was not persisted.")

            part_count = (
                await conn.execute(
                    text(
                        "select count(*) from part_results "
                        "where item_id = :item_id and site = :site"
                    ),
                    {"item_id": item_row["id"], "site": case.site},
                )
            ).scalar_one()

            if case.expect_result and part_count < 1:
                _fail(f"Case {case.id} expected persisted part_results.")
            if not case.expect_result and part_count != 0:
                _fail(f"Case {case.id} expected zero persisted part_results.")
    finally:
        await engine.dispose()


async def _run(args: argparse.Namespace) -> None:
    manifest_path = Path(args.manifest)
    cases = _load_manifest(manifest_path)
    _credential_gate(cases)

    api_key = args.api_key or os.environ.get("API_KEY")
    if not api_key:
        _fail("API key is required via --api-key or API_KEY.")

    database_url = args.database_url or os.environ.get("DATABASE_URL")
    if not database_url:
        _fail("Database URL is required via --database-url or DATABASE_URL.")

    async with httpx.AsyncClient(base_url=args.base_url, timeout=30) as client:
        health = await client.get("/api/v1/health")
        health.raise_for_status()

        passed = 0
        for case in cases:
            print(f"[{case.id}] submitting {case.site}:{case.sku}")
            job_id = await _submit_job(client, api_key, case)
            job = await _wait_for_job(client, api_key, job_id, args.timeout_seconds)
            _validate_api_result(job, case)
            await _validate_database(database_url, job_id, case)
            print(f"[{case.id}] passed job_id={job_id} status={job['status']}")
            passed += 1

    print(f"Validated {passed} local scraper cases from {manifest_path}.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, help="Path to validation manifest JSON.")
    parser.add_argument("--base-url", default="http://localhost:8000", help="Local API base URL.")
    parser.add_argument("--api-key", default="", help="API key. Defaults to API_KEY env var.")
    parser.add_argument(
        "--database-url",
        default="",
        help="Async SQLAlchemy database URL. Defaults to DATABASE_URL env var.",
    )
    parser.add_argument("--timeout-seconds", type=float, default=180.0)
    args = parser.parse_args()

    try:
        asyncio.run(_run(args))
    except Exception as exc:
        print(f"validation failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
