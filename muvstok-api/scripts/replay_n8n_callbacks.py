#!/usr/bin/env python3
"""Replay Muvstok job callbacks to n8n so Google Sheets receive missed rows.

Usage:
  source .env
  uv run python scripts/replay_n8n_callbacks.py --since 2026-05-21 --limit 40
  uv run python scripts/replay_n8n_callbacks.py --job-id <uuid>
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import selectinload

from app.db.models import MuvstokApiData, MuvstokJob, MuvstokJobItem
from app.domain.job_status import JobStatus


def _webhook_url() -> str:
    url = os.environ.get("CDP_MUVSTOK_N8N_WEBHOOK_URL", "").strip()
    if url:
        return url
    base = os.environ.get("WEBHOOK_URL", "https://automacao.tktechnologies.com.br").rstrip("/")
    path = os.environ.get("CDP_MUVSTOK_WEBHOOK_PATH", "webhook/muvstok-result").strip("/")
    return f"{base}/{path}?notify=none"


def _secret() -> str:
    for key in (
        "CALLBACK_WEBHOOK_SECRET",
        "CDP_MUVSTOK_CALLBACK_WEBHOOK_SECRET",
        "CDP_CALLBACK_WEBHOOK_SECRET",
    ):
        value = os.environ.get(key, "").strip()
        if value:
            return value
    print("Set CALLBACK_WEBHOOK_SECRET in environment", file=sys.stderr)
    sys.exit(1)


def _n8n_headers() -> dict[str, str]:
    key = os.environ.get("N8N_API_KEY", "").strip()
    if not key:
        return {}
    return {"X-N8N-API-KEY": key, "Accept": "application/json"}


def _post_callback(payload: dict[str, Any]) -> int:
    body = json.dumps(payload, default=str).encode()
    req = urllib.request.Request(
        _webhook_url(),
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "x-webhook-secret": _secret(),
        },
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.status


def _latest_receiver_execution() -> dict[str, Any] | None:
    base = os.environ.get("N8N_BASE_URL", "").strip().rstrip("/")
    key = os.environ.get("N8N_API_KEY", "").strip()
    if not base or not key:
        return None
    url = f"{base}/api/v1/executions?workflowId=t160mzGPYYlJcrjZ&limit=1"
    req = urllib.request.Request(url, headers=_n8n_headers())
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.load(resp)
        if not data.get("data"):
            return None
        eid = data["data"][0]["id"]
        url2 = f"{base}/api/v1/executions/{eid}?includeData=true"
        with urllib.request.urlopen(urllib.request.Request(url2, headers=_n8n_headers()), timeout=60) as resp:
            return json.load(resp)
    except urllib.error.URLError:
        return None


def _execution_ok(ex: dict[str, Any] | None) -> tuple[bool, str]:
    if not ex:
        return False, "no n8n execution data"
    rd = ex.get("data", {}).get("resultData", {})
    last = rd.get("lastNodeExecuted", "")
    if last in ("🚫 Secret inválido",):
        return False, f"blocked at {last}"
    run = rd.get("runData", {})
    required = (
        "📊 Salvar → CDP_Resultados (Detalhado)",
        "📊 Salvar → CDP_Resultados (Historico)",
        "✅ Atualizar CDP_SKUs",
    )
    missing = []
    for node in required:
        if node not in run:
            missing.append(node)
            continue
        st = run[node][0].get("executionStatus")
        err = run[node][0].get("error")
        if st != "success":
            missing.append(f"{node}:{st}:{(err or {}).get('message', '')[:40]}")
    if missing:
        return False, "; ".join(missing)
    return True, last or "ok"


def _build_payload_from_api(job_json: dict[str, Any]) -> dict[str, Any]:
    items = job_json.get("items") or []
    callback_items = []
    results = []
    for item in items:
        sku = item["sku"]
        st = item.get("status", "failed")
        ok = st == "succeeded"
        callback_items.append(
            {
                "sku": sku,
                "status": "succeeded" if ok else "failed",
                "snapshot_id": None,
                "error_code": item.get("last_error_code"),
            }
        )
        results.append({"sku": sku, "status": "succeeded" if ok else "failed", "rows": []})
    succeeded = sum(1 for i in callback_items if i["status"] == "succeeded")
    failed = len(callback_items) - succeeded
    meta = dict(job_json.get("metadata") or {})
    meta["replay"] = True
    meta["replay_at"] = datetime.now(UTC).isoformat()
    meta["replay_source"] = "api"
    return {
        "job_id": job_json["job_id"],
        "correlation_id": job_json["correlation_id"],
        "status": job_json["status"],
        "submitted_sku_count": job_json["submitted_sku_count"],
        "succeeded_sku_count": succeeded,
        "failed_sku_count": failed,
        "items": callback_items,
        "results": results,
        "metadata": meta,
        "completed_at": job_json.get("updated_at", datetime.now(UTC).isoformat()),
    }


def _fetch_job_api(job_id: str) -> dict[str, Any]:
    base = os.environ.get("CDP_MUVSTOK_API_BASE", "").rstrip("/")
    key = os.environ.get("CDP_MUVSTOK_API_KEY") or os.environ.get("API_KEYS", "").split(",")[0].strip()
    url = f"{base}/api/v1/muvstok/jobs/{job_id}"
    req = urllib.request.Request(url, headers={"X-API-Key": key, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)


def _build_payload(job: MuvstokJob, items: list[MuvstokJobItem], api_rows: list[MuvstokApiData]) -> dict[str, Any]:
    api_by_item = {row.job_item_id: row for row in api_rows}
    sku_results: list[dict[str, Any]] = []
    callback_items: list[dict[str, Any]] = []

    for item in items:
        status = item.status.value if hasattr(item.status, "value") else str(item.status)
        error_code = item.last_error_code
        callback_items.append(
            {
                "sku": item.sku,
                "status": "succeeded" if status == "succeeded" else "failed",
                "snapshot_id": None,
                "error_code": error_code,
            }
        )
        rows: list[dict[str, Any]] = []
        api_row = api_by_item.get(item.id)
        if api_row and api_row.muvstok_payload:
            payload = api_row.muvstok_payload
            if isinstance(payload, dict):
                raw_rows = payload.get("rows")
                if isinstance(raw_rows, list):
                    rows = raw_rows
        duration_ms = 0
        if api_row and isinstance(api_row.response_metadata, dict):
            duration_ms = int(api_row.response_metadata.get("duration_ms") or 0)
        sku_results.append(
            {
                "sku": item.sku,
                "status": "succeeded" if status == "succeeded" else "failed",
                "rows": rows,
                "duration_ms": duration_ms,
            }
        )

    succeeded = sum(1 for i in callback_items if i["status"] == "succeeded")
    failed = len(callback_items) - succeeded
    status = job.status.value if hasattr(job.status, "value") else str(job.status)
    completed = job.updated_at or datetime.now(UTC)
    meta = dict(job.metadata_json or {})
    meta["replay"] = True
    meta["replay_at"] = datetime.now(UTC).isoformat()

    started = job.created_at or completed
    duration_seconds = None
    if started and completed and completed >= started:
        duration_seconds = round((completed - started).total_seconds(), 2)

    return {
        "job_id": str(job.id),
        "correlation_id": job.correlation_id,
        "status": status,
        "submitted_sku_count": job.submitted_sku_count,
        "succeeded_sku_count": succeeded,
        "failed_sku_count": failed,
        "items": callback_items,
        "results": sku_results,
        "metadata": meta,
        "started_at": started.isoformat().replace("+00:00", "Z"),
        "duration_seconds": duration_seconds,
        "completed_at": completed.isoformat().replace("+00:00", "Z"),
    }


async def _load_jobs(
    *,
    database_url: str,
    since: datetime | None,
    job_id: UUID | None,
    limit: int,
) -> list[tuple[MuvstokJob, list[MuvstokJobItem], list[MuvstokApiData]]]:
    engine = create_async_engine(
        database_url,
        connect_args={"connect_timeout": 90},
    )
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    out: list[tuple[MuvstokJob, list[MuvstokJobItem], list[MuvstokApiData]]] = []
    try:
        async with session_factory() as session:
            stmt = select(MuvstokJob).options(selectinload(MuvstokJob.items))
            if job_id:
                stmt = stmt.where(MuvstokJob.id == job_id)
            else:
                stmt = stmt.where(
                    MuvstokJob.status.in_(
                        [
                            JobStatus.SUCCEEDED,
                            JobStatus.PARTIALLY_SUCCEEDED,
                            JobStatus.FAILED,
                        ]
                    )
                )
                if since:
                    stmt = stmt.where(MuvstokJob.updated_at >= since)
                stmt = stmt.order_by(MuvstokJob.updated_at.desc()).limit(limit)

            jobs = list((await session.execute(stmt)).scalars().unique().all())
            for job in jobs:
                api_stmt = select(MuvstokApiData).where(MuvstokApiData.job_id == job.id)
                api_rows = list((await session.execute(api_stmt)).scalars().all())
                out.append((job, list(job.items), api_rows))
    finally:
        await engine.dispose()
    return out


async def main() -> int:
    parser = argparse.ArgumentParser(description="Replay callbacks to n8n receiver")
    parser.add_argument("--since", default="2026-05-21", help="ISO date (UTC) for job filter")
    parser.add_argument("--limit", type=int, default=30, help="Max jobs to replay")
    parser.add_argument("--job-id", help="Replay a single job UUID")
    parser.add_argument(
        "--job-ids",
        help="Comma-separated job UUIDs (uses API; no DB). Fetches status/items only.",
    )
    parser.add_argument("--delay", type=float, default=3.0, help="Seconds between replays")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    payloads: list[dict[str, Any]] = []
    if args.job_ids or args.job_id:
        ids = []
        if args.job_id:
            ids.append(args.job_id.strip())
        if args.job_ids:
            ids.extend([part.strip() for part in args.job_ids.split(",") if part.strip()])
        for jid in ids:
            job_json = _fetch_job_api(jid)
            payloads.append(_build_payload_from_api(job_json))
    else:
        database_url = os.environ.get("DATABASE_URL", "").strip()
        if not database_url:
            print("DATABASE_URL or --job-ids required", file=sys.stderr)
            return 1
        since_dt = datetime.fromisoformat(args.since).replace(tzinfo=UTC)
        bundles = await _load_jobs(
            database_url=database_url,
            since=since_dt,
            job_id=None,
            limit=args.limit,
        )
        for job, items, api_rows in bundles:
            payloads.append(_build_payload(job, items, api_rows))

    print(f"jobs_to_replay={len(payloads)} webhook={_webhook_url()}")

    ok_count = 0
    fail_count = 0
    for payload in payloads:
        print(
            f"\njob {payload['job_id']} status={payload['status']} "
            f"ok={payload['succeeded_sku_count']} fail={payload['failed_sku_count']}"
        )
        if args.dry_run:
            continue
        try:
            status = _post_callback(payload)
            print(f"  POST http={status}")
        except urllib.error.HTTPError as exc:
            print(f"  POST failed http={exc.code} {exc.read()[:200]}")
            fail_count += 1
            continue
        time.sleep(max(args.delay, 1.0))
        ex = _latest_receiver_execution()
        good, detail = _execution_ok(ex)
        print(f"  n8n {'PASS' if good else 'FAIL'}: {detail}")
        if good:
            ok_count += 1
        else:
            fail_count += 1

    print(f"\nreplay_summary ok={ok_count} fail={fail_count} total={len(payloads)}")
    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
