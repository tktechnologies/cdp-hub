#!/usr/bin/env python3
"""Generate DEV n8n workflow JSON copies from production workflows in n8n/workflows/."""
from __future__ import annotations

import argparse
import copy
import json
import os
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_DIR = REPO_ROOT / "n8n" / "workflows"
DEV_DIR = WORKFLOW_DIR / "dev"

PROD_TELEGRAM_CREDENTIAL_ID = "UmDqGKD8k0bA10j2"
PROD_SKUS_SHEET_ID = "1IGhsIhrwlnMaCduR-W-eIi9O4mMO2pPYjE-tefgIPII"
PROD_RESULTADOS_SHEET_ID = "1ZBU2d3XVsngOYQH12yU7Mg9DcIzVet2dDmhMtZqHSOo"

DEFAULT_TELEGRAM_CREDENTIAL_PLACEHOLDER = "__SET_N8N_DEV_TELEGRAM_CREDENTIAL_ID__"
DEFAULT_SKUS_SHEET_PLACEHOLDER = "__SET_CDP_DEV_SKUS_SHEET_ID__"
DEFAULT_RESULTADOS_SHEET_PLACEHOLDER = "__SET_CDP_DEV_RESULTADOS_SHEET_ID__"

WORKFLOWS: dict[str, dict[str, Path | str]] = {
    "router": {
        "src": WORKFLOW_DIR / "cdp_router.json",
        "dest": DEV_DIR / "dev_cdp_router.json",
        "name": "DEV - cdp_router",
    },
    "scraper": {
        "src": WORKFLOW_DIR / "cdp_scraper.json",
        "dest": DEV_DIR / "dev_cdp_scraper.json",
        "name": "DEV - cdp_scraper",
    },
    "stokapi": {
        "src": WORKFLOW_DIR / "cdp_stokapi.json",
        "dest": DEV_DIR / "dev_cdp_stokapi.json",
        "name": "DEV - cdp_stokapi",
    },
    "progress": {
        "src": WORKFLOW_DIR / "cdp_progress.json",
        "dest": DEV_DIR / "dev_cdp_progress.json",
        "name": "DEV - cdp_progress",
    },
    "notifier": {
        "src": WORKFLOW_DIR / "cdp_notifier.json",
        "dest": DEV_DIR / "dev_cdp_notifier.json",
        "name": "DEV - cdp_notifier",
    },
}


def _telegram_credential_id() -> str:
    value = os.environ.get("N8N_DEV_TELEGRAM_CREDENTIAL_ID", "").strip()
    return value or DEFAULT_TELEGRAM_CREDENTIAL_PLACEHOLDER


def _sheet_id(env_name: str, placeholder: str) -> str:
    value = os.environ.get(env_name, "").strip()
    return value or placeholder


def _replace_strings(value: Any, mapping: dict[str, str]) -> Any:
    if isinstance(value, str):
        out = value
        for old, new in mapping.items():
            out = out.replace(old, new)
        return out
    if isinstance(value, list):
        return [_replace_strings(item, mapping) for item in value]
    if isinstance(value, dict):
        return {key: _replace_strings(item, mapping) for key, item in value.items()}
    return value


def _patch_telegram_credentials(wf: dict[str, Any], credential_id: str) -> None:
    credential_name = os.environ.get("N8N_DEV_TELEGRAM_CREDENTIAL_NAME", "dev-cdp-bot").strip()
    for node in wf.get("nodes", []):
        credentials = node.get("credentials")
        if not isinstance(credentials, dict):
            continue
        telegram = credentials.get("telegramApi")
        if not isinstance(telegram, dict):
            continue
        telegram["id"] = credential_id
        telegram["name"] = credential_name


def _patch_sheet_ids(wf: dict[str, Any], skus_sheet_id: str, resultados_sheet_id: str) -> None:
    mapping = {
        PROD_SKUS_SHEET_ID: skus_sheet_id,
        PROD_RESULTADOS_SHEET_ID: resultados_sheet_id,
    }
    patched = _replace_strings(wf, mapping)
    wf.clear()
    wf.update(patched)


def _regenerate_webhook_ids(wf: dict[str, Any]) -> None:
    """DEV copies must not reuse prod webhookIds (n8n activate returns 409)."""
    import uuid

    for node in wf.get("nodes", []):
        if "webhookId" in node:
            node["webhookId"] = str(uuid.uuid4())


def _disable_router_non_telegram_triggers(wf: dict[str, Any]) -> None:
    for node in wf.get("nodes", []):
        if node.get("type") in {"n8n-nodes-base.gmailTrigger", "n8n-nodes-base.scheduleTrigger"}:
            node["disabled"] = True


def _disable_notifier_gmail(wf: dict[str, Any]) -> None:
    for node in wf.get("nodes", []):
        if node.get("type") == "n8n-nodes-base.gmail":
            node["disabled"] = True


def _patch_receiver_webhooks(wf: dict[str, Any], *, old_path: str, new_path: str) -> None:
    for node in wf.get("nodes", []):
        if node.get("type") != "n8n-nodes-base.webhook":
            continue
        params = node.setdefault("parameters", {})
        if params.get("path") == old_path:
            params["path"] = new_path
        if node.get("webhookId") == old_path:
            node["webhookId"] = new_path


def _patch_progress_schedule(wf: dict[str, Any]) -> None:
    for node in wf.get("nodes", []):
        if node.get("type") != "n8n-nodes-base.scheduleTrigger":
            continue
        params = node.setdefault("parameters", {})
        rule = params.setdefault("rule", {})
        intervals = rule.setdefault("interval", [])
        if not intervals:
            intervals.append({})
        intervals[0]["field"] = "minutes"
        intervals[0]["minutesInterval"] = (
            "={{ Number($env.CDP_DEV_PROGRESS_INTERVAL_MIN || $env.CDP_PROGRESS_INTERVAL_MIN || 10) }}"
        )


def _strip_import_metadata(wf: dict[str, Any]) -> None:
    for key in ("id", "versionId", "meta", "pinData", "tags"):
        wf.pop(key, None)


def transform_workflow(
    wf: dict[str, Any],
    *,
    kind: str,
    dev_name: str,
    credential_id: str,
    skus_sheet_id: str,
    resultados_sheet_id: str,
) -> dict[str, Any]:
    out = copy.deepcopy(wf)
    out["name"] = dev_name
    _strip_import_metadata(out)
    _patch_telegram_credentials(out, credential_id)
    _patch_sheet_ids(out, skus_sheet_id, resultados_sheet_id)

    if kind == "router":
        _regenerate_webhook_ids(out)
        _disable_router_non_telegram_triggers(out)
    elif kind == "scraper":
        _patch_receiver_webhooks(out, old_path="scraper-result", new_path="dev-scraper-result")
    elif kind == "stokapi":
        _patch_receiver_webhooks(out, old_path="muvstok-result", new_path="dev-muvstok-result")
    elif kind == "progress":
        _patch_progress_schedule(out)
    elif kind == "notifier":
        _patch_receiver_webhooks(out, old_path="cdp-notifier", new_path="dev-cdp-notifier")
        _disable_notifier_gmail(out)
    return out


def audit_dev_workflow(wf: dict[str, Any], *, kind: str, credential_id: str) -> list[str]:
    problems: list[str] = []
    blob = json.dumps(wf, ensure_ascii=False)

    if PROD_TELEGRAM_CREDENTIAL_ID in blob:
        problems.append(f"{kind}: production Telegram credential id remains in DEV JSON")
    if PROD_SKUS_SHEET_ID in blob:
        problems.append(f"{kind}: production SKUs sheet id remains in DEV JSON")
    if PROD_RESULTADOS_SHEET_ID in blob:
        problems.append(f"{kind}: production resultados sheet id remains in DEV JSON")

    if kind == "scraper" and '"scraper-result"' in blob:
        problems.append("scraper: production webhook path remains in DEV JSON")
    if kind == "stokapi" and '"muvstok-result"' in blob:
        problems.append("stokapi: production webhook path remains in DEV JSON")
    if kind == "notifier":
        for node in wf.get("nodes", []):
            if node.get("type") != "n8n-nodes-base.webhook":
                continue
            path = node.get("parameters", {}).get("path")
            if path == "cdp-notifier":
                problems.append("notifier: production webhook path remains in DEV JSON")

    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--require-telegram-credential",
        action="store_true",
        help="Exit with code 1 when N8N_DEV_TELEGRAM_CREDENTIAL_ID is unset",
    )
    args = parser.parse_args(argv)

    credential_id = _telegram_credential_id()
    if args.require_telegram_credential:
        env_value = os.environ.get("N8N_DEV_TELEGRAM_CREDENTIAL_ID", "").strip()
        if not env_value:
            print(
                "N8N_DEV_TELEGRAM_CREDENTIAL_ID is required for import-n8n-dev "
                "(create or select the dev-cdp-bot Telegram credential in n8n first).",
                file=sys.stderr,
            )
            return 1

    skus_sheet_id = _sheet_id("CDP_DEV_SKUS_SHEET_ID", DEFAULT_SKUS_SHEET_PLACEHOLDER)
    resultados_sheet_id = _sheet_id(
        "CDP_DEV_RESULTADOS_SHEET_ID",
        DEFAULT_RESULTADOS_SHEET_PLACEHOLDER,
    )

    DEV_DIR.mkdir(parents=True, exist_ok=True)
    failures: list[str] = []

    for kind, spec in WORKFLOWS.items():
        src = Path(spec["src"])
        dest = Path(spec["dest"])
        dev_name = str(spec["name"])

        if not src.is_file():
            failures.append(f"{kind}: missing source workflow {src}")
            continue

        wf = json.loads(src.read_text(encoding="utf-8"))
        dev_wf = transform_workflow(
            wf,
            kind=kind,
            dev_name=dev_name,
            credential_id=credential_id,
            skus_sheet_id=skus_sheet_id,
            resultados_sheet_id=resultados_sheet_id,
        )
        problems = audit_dev_workflow(dev_wf, kind=kind, credential_id=credential_id)
        if problems:
            failures.extend(problems)
            continue

        dest.write_text(json.dumps(dev_wf, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {dest.relative_to(REPO_ROOT)} ({len(dev_wf.get('nodes', []))} nodes)")

    if failures:
        print("DEV workflow generation failed:", file=sys.stderr)
        for problem in failures:
            print(f"  - {problem}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
