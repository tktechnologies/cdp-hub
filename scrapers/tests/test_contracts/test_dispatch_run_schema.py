"""Contract tests: dispatch-run registry (dual-pipeline progress)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import jsonschema

from src.models.schemas import (
    DispatchRunProgressUpdate,
    DispatchRunResponse,
    DispatchRunUpsertRequest,
)

CONTRACTS_DIR = Path(__file__).resolve().parents[3] / "contracts"


def _load_schema() -> dict:
    return json.loads((CONTRACTS_DIR / "dispatch-run.schema.json").read_text(encoding="utf-8"))


def test_dispatch_run_upsert_matches_schema() -> None:
    schema = _load_schema()
    request = DispatchRunUpsertRequest(
        batch_group_id="batch-1",
        chat_id="12345",
        command_route="analisar",
        scraper_job_ids=["job-a"],
        stokapi_job_id="job-b",
        total_skus=10,
        estimated_seconds=600,
        dispatched_at=datetime.now(UTC),
    )
    jsonschema.validate(
        request.model_dump(mode="json"),
        schema["$defs"]["DispatchRunUpsertRequest"],
    )


def test_dispatch_run_response_matches_schema() -> None:
    schema = _load_schema()
    response = DispatchRunResponse(
        id="run-1",
        batch_group_id="batch-1",
        chat_id="12345",
        command_route="analisar",
        scraper_job_ids=["job-a"],
        stokapi_job_id="job-b",
        total_skus=10,
        dispatched_at=datetime.now(UTC),
        estimated_seconds=600,
        scraper_status="processing",
        stokapi_status="pending",
        last_progress_pct=25.0,
    )
    jsonschema.validate(
        response.model_dump(mode="json"),
        schema["$defs"]["DispatchRunResponse"],
    )


def test_dispatch_run_progress_update_matches_schema() -> None:
    schema = _load_schema()
    update = DispatchRunProgressUpdate(
        last_progress_pct=50.0,
        progress_message_count=2,
        scraper_status="completed",
        stokapi_status="processing",
    )
    jsonschema.validate(
        update.model_dump(mode="json"),
        schema["$defs"]["DispatchRunProgressUpdate"],
    )
