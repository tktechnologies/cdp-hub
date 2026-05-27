"""Validate StokAPI payloads against shared JSON Schema contracts."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import jsonschema

from app.domain.job_status import JobStatus
from app.schemas.callbacks import CallbackJobItem, MuvstokCallbackPayload
from app.schemas.requests import CreateMuvstokJobRequest

CONTRACTS_DIR = Path(__file__).resolve().parents[3] / "contracts"


def _load_schema(name: str) -> dict:
    return json.loads((CONTRACTS_DIR / name).read_text(encoding="utf-8"))


def test_stokapi_job_request_matches_schema() -> None:
    request = CreateMuvstokJobRequest(
        skus=["93338835", "A0001234567"],
        callback_url="https://example.com/webhook/muvstok-result",
        metadata={"chat_id": "99"},
        idempotency_key="batch-1",
    )
    payload = request.model_dump(mode="json")
    jsonschema.validate(payload, _load_schema("stokapi-job.schema.json"))


def test_muvstok_callback_payload_matches_schema() -> None:
    payload = MuvstokCallbackPayload(
        job_id=uuid4(),
        correlation_id="corr-callback",
        status=JobStatus.SUCCEEDED.value,
        submitted_sku_count=2,
        succeeded_sku_count=2,
        failed_sku_count=0,
        items=[
            CallbackJobItem(sku="93338835", status="succeeded", snapshot_id=uuid4()),
            CallbackJobItem(sku="A0001234567", status="succeeded", snapshot_id=uuid4()),
        ],
        results=[{"sku": "93338835", "status": "succeeded", "rows": [], "duration_ms": 120}],
        metadata={"chat_id": "99", "notify": "telegram"},
        started_at=datetime.now(UTC),
        duration_seconds=1.5,
        completed_at=datetime.now(UTC),
    )
    jsonschema.validate(
        payload.model_dump(mode="json"),
        _load_schema("stokapi-callback.schema.json"),
    )
