"""Contract tests: scraper job request and callback payloads."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import jsonschema

from src.models.schemas import (
    Currency,
    ItemCondition,
    JobStatus,
    PartResult,
    ScrapeJobRequest,
    ScrapeJobResult,
    SiteId,
    SiteResult,
    SKUItem,
    SKUResult,
)

CONTRACTS_DIR = Path(__file__).resolve().parents[3] / "contracts"


def _load_schema(name: str) -> dict:
    return json.loads((CONTRACTS_DIR / name).read_text(encoding="utf-8"))


def test_scrape_job_request_matches_schema() -> None:
    request = ScrapeJobRequest(
        items=[SKUItem(sku="93338835", brand="GM"), SKUItem(sku="A0001234567", brand="Mercedes")],
        sites=[SiteId.GM, SiteId.MERCADO_LIVRE],
        callback_url="https://example.com/webhook/scraper-result",
        force_refresh=False,
        chat_id="123",
        command_route="analisar",
    )
    jsonschema.validate(
        request.model_dump(mode="json"),
        _load_schema("scraper-job.schema.json"),
    )


def test_scrape_job_callback_payload_matches_schema() -> None:
    part = PartResult(
        sku_searched="93338835",
        sku_found="93338835",
        exact_match=True,
        site=SiteId.GM,
        site_name="GM Parts Dealer",
        price=150.5,
        currency=Currency.BRL,
        condition=ItemCondition.NEW,
        availability="in_stock",
        origin="Brasil",
    )
    site_result = SiteResult(
        site=SiteId.GM,
        site_name="GM Parts Dealer",
        status="success",
        results=[part],
        search_time_ms=1200,
    )
    sku_result = SKUResult(
        sku="93338835",
        brand="GM",
        site_results=[site_result],
        total_results=1,
        cache_hits=0,
        live_scrapes=1,
    )
    payload = ScrapeJobResult(
        job_id="job-contract-1",
        status=JobStatus.COMPLETED,
        results=[sku_result],
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
        duration_seconds=12.5,
        total_items=1,
        items_succeeded=1,
        items_failed=0,
        items_processed=1,
        progress_pct=100.0,
        sku_success_count=1,
    )
    jsonschema.validate(
        payload.model_dump(mode="json"),
        _load_schema("scraper-callback.schema.json"),
    )
