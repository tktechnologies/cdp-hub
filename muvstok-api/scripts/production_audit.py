#!/usr/bin/env python3
"""Production audit helper: submit a small SKU job and verify API terminal state.

Usage:
  source .env
  uv run python scripts/production_audit.py --skus "7703062062,661003M6M00ZZ"
  uv run python scripts/production_audit.py --skus-file /path/to/skus.txt --source prod-audit

Does not read Google Sheets; use n8n sender for sheet-driven audits.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def _api_key() -> str:
    key = _env("CDP_MUVSTOK_API_KEY") or _env("API_KEYS").split(",")[0].strip()
    if not key:
        print("Set CDP_MUVSTOK_API_KEY or API_KEYS in environment", file=sys.stderr)
        sys.exit(1)
    return key


def _base_url() -> str:
    return _env(
        "CDP_MUVSTOK_API_BASE",
        "https://cdp-muv-api.bravecoast-b14d791e.eastus2.azurecontainerapps.io",
    ).rstrip("/")


def _callback_url() -> str:
    url = _env("CDP_MUVSTOK_N8N_WEBHOOK_URL")
    if url:
        return url
    base = _env("WEBHOOK_URL", "https://automacao.tktechnologies.com.br").rstrip("/")
    path = _env("CDP_MUVSTOK_WEBHOOK_PATH", "webhook/muvstok-result").strip("/")
    return f"{base}/{path}?notify=telegram"


def _http_json(
    method: str,
    url: str,
    *,
    api_key: str,
    body: dict | None = None,
    timeout: float = 30.0,
) -> tuple[int, dict]:
    data = None
    headers = {"X-API-Key": api_key, "Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        try:
            payload = json.loads(raw) if raw else {"detail": exc.reason}
        except json.JSONDecodeError:
            payload = {"detail": raw or exc.reason}
        return exc.code, payload


def _load_skus(args: argparse.Namespace) -> list[str]:
    if args.skus:
        return [s.strip() for s in args.skus.split(",") if s.strip()]
    if args.skus_file:
        with open(args.skus_file, encoding="utf-8") as fh:
            return [line.strip() for line in fh if line.strip() and not line.startswith("#")]
    print("Provide --skus or --skus-file", file=sys.stderr)
    sys.exit(1)


def main() -> int:
    parser = argparse.ArgumentParser(description="Muvstok production audit (small SKU job)")
    parser.add_argument("--skus", help="Comma-separated SKU list")
    parser.add_argument("--skus-file", help="One SKU per line")
    parser.add_argument("--source", default="production-audit", help="metadata.source value")
    parser.add_argument("--timeout", type=int, default=180, help="Max seconds to poll job")
    parser.add_argument("--poll-interval", type=float, default=5.0)
    parser.add_argument("--dry-run", action="store_true", help="Health check only")
    args = parser.parse_args()

    base = _base_url()
    key = _api_key()
    skus = _load_skus(args)

    print(f"base={base}")
    print(f"sku_count={len(skus)}")

    status, health = _http_json("GET", f"{base}/api/v1/muvstok/health", api_key=key)
    print(f"[{'PASS' if status == 200 else 'FAIL'}] health http={status} body={health}")
    if status != 200:
        return 1
    if args.dry_run:
        return 0

    idem = f"audit-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"
    body = {
        "skus": skus,
        "callback_url": _callback_url(),
        "metadata": {"source": args.source, "audit_id": idem},
        "idempotency_key": idem,
    }
    status, accepted = _http_json("POST", f"{base}/api/v1/muvstok/jobs", api_key=key, body=body)
    print(f"[{'PASS' if status == 202 else 'FAIL'}] create_job http={status}")
    print(json.dumps(accepted, indent=2))
    if status != 202 or "job_id" not in accepted:
        return 1

    job_id = accepted["job_id"]
    deadline = time.monotonic() + args.timeout
    terminal = {"succeeded", "failed", "partially_succeeded", "canceled"}
    last: dict = {}

    while time.monotonic() < deadline:
        time.sleep(args.poll_interval)
        status, last = _http_json("GET", f"{base}/api/v1/muvstok/jobs/{job_id}", api_key=key)
        if status != 200:
            print(f"[FAIL] get_job http={status} {last}")
            return 1
        job_status = last.get("status", "")
        print(
            f"  poll status={job_status} ok={last.get('succeeded_sku_count')} "
            f"fail={last.get('failed_sku_count')} callback={last.get('callback_status')}"
        )
        if job_status in terminal:
            break
    else:
        print("[FAIL] timeout waiting for terminal job status")
        return 1

    print("\n--- per-SKU ---")
    for item in last.get("items") or []:
        mark = "OK" if item.get("status") == "succeeded" else "!!"
        print(
            f"  [{mark}] sku={item.get('sku')} status={item.get('status')} "
            f"error={item.get('last_error_code')}"
        )

    callback_ok = last.get("callback_status") == "succeeded"
    job_ok = last.get("status") in terminal
    print("\n--- summary ---")
    print(f"  job_id={job_id}")
    print(f"  correlation_id={last.get('correlation_id')}")
    print(f"  job_status={last.get('status')}")
    print(f"  callback_status={last.get('callback_status')}")
    print(f"  [{'PASS' if callback_ok else 'FAIL'}] callback delivered")
    print(f"  [{'PASS' if job_ok else 'FAIL'}] job terminal")

    print("\nNext manual checks:")
    print("  - n8n receiver execution (workflow t160mzGPYYlJcrjZ) after callback")
    print("  - Google Sheets cdp_skus / cdp_resultados for these SKUs")
    print("  - SQL: muvstok_jobs, muvstok_job_items, muvstok_raw_snapshots, muvstok_api_data")

    return 0 if job_ok and callback_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
