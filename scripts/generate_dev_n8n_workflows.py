#!/usr/bin/env python3
"""Generate target n8n workflow JSON copies from production workflows."""
from __future__ import annotations

import argparse
import copy
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_DIR = REPO_ROOT / "n8n" / "workflows"

PROD_TELEGRAM_CREDENTIAL_ID = "UmDqGKD8k0bA10j2"
PROD_TELEGRAM_CREDENTIAL_NAME = "cdp-bot-assistente"
PROD_SKUS_SHEET_ID = "1IGhsIhrwlnMaCduR-W-eIi9O4mMO2pPYjE-tefgIPII"
PROD_RESULTADOS_SHEET_ID = "1ZBU2d3XVsngOYQH12yU7Mg9DcIzVet2dDmhMtZqHSOo"

DEFAULT_DEV_TELEGRAM_CREDENTIAL_PLACEHOLDER = "__SET_N8N_DEV_TELEGRAM_CREDENTIAL_ID__"
DEFAULT_DEV_SKUS_SHEET_PLACEHOLDER = "__SET_CDP_DEV_SKUS_SHEET_ID__"
DEFAULT_DEV_RESULTADOS_SHEET_PLACEHOLDER = "__SET_CDP_DEV_RESULTADOS_SHEET_ID__"

KINDS = ("router", "scraper", "stokapi", "progress", "notifier")
SOURCE_BY_KIND = {
    "router": WORKFLOW_DIR / "cdp_router.json",
    "scraper": WORKFLOW_DIR / "cdp_scraper.json",
    "stokapi": WORKFLOW_DIR / "cdp_stokapi.json",
    "progress": WORKFLOW_DIR / "cdp_progress.json",
    "notifier": WORKFLOW_DIR / "cdp_notifier.json",
}


@dataclass(frozen=True)
class TargetConfig:
    key: str
    dir_name: str
    file_prefix: str
    workflow_prefix: str
    scraper_webhook_path: str
    stokapi_webhook_path: str
    notifier_webhook_path: str
    progress_interval_env: str
    telegram_credential_id: str
    telegram_credential_name: str
    skus_sheet_id: str
    resultados_sheet_id: str
    forbid_prod_telegram: bool = False
    forbid_prod_sheets: bool = False
    disable_router_non_telegram_triggers: bool = False
    disable_notifier_gmail: bool = False


def target_config(target: str) -> TargetConfig:
    if target == "dev":
        credential_id = (
            os.environ.get("N8N_DEV_TELEGRAM_CREDENTIAL_ID", "").strip()
            or DEFAULT_DEV_TELEGRAM_CREDENTIAL_PLACEHOLDER
        )
        return TargetConfig(
            key="dev",
            dir_name="dev",
            file_prefix="dev",
            workflow_prefix="DEV - ",
            scraper_webhook_path="dev-scraper-result",
            stokapi_webhook_path="dev-muvstok-result",
            notifier_webhook_path="dev-cdp-notifier",
            progress_interval_env="CDP_DEV_PROGRESS_INTERVAL_MIN",
            telegram_credential_id=credential_id,
            telegram_credential_name=os.environ.get(
                "N8N_DEV_TELEGRAM_CREDENTIAL_NAME",
                "dev-cdp-bot",
            ).strip(),
            skus_sheet_id=os.environ.get(
                "CDP_DEV_SKUS_SHEET_ID",
                DEFAULT_DEV_SKUS_SHEET_PLACEHOLDER,
            ).strip(),
            resultados_sheet_id=os.environ.get(
                "CDP_DEV_RESULTADOS_SHEET_ID",
                DEFAULT_DEV_RESULTADOS_SHEET_PLACEHOLDER,
            ).strip(),
            forbid_prod_telegram=True,
            forbid_prod_sheets=True,
            disable_router_non_telegram_triggers=True,
            disable_notifier_gmail=True,
        )

    if target == "stokai":
        return TargetConfig(
            key="stokai",
            dir_name="stokai",
            file_prefix="stokai",
            workflow_prefix="STOKAI - ",
            scraper_webhook_path="stokai-scraper-result",
            stokapi_webhook_path="stokai-muvstok-result",
            notifier_webhook_path="stokai-cdp-notifier",
            progress_interval_env="CDP_STOKAI_PROGRESS_INTERVAL_MIN",
            telegram_credential_id=os.environ.get(
                "N8N_STOKAI_TELEGRAM_CREDENTIAL_ID",
                PROD_TELEGRAM_CREDENTIAL_ID,
            ).strip(),
            telegram_credential_name=os.environ.get(
                "N8N_STOKAI_TELEGRAM_CREDENTIAL_NAME",
                PROD_TELEGRAM_CREDENTIAL_NAME,
            ).strip(),
            skus_sheet_id=os.environ.get("CDP_STOKAI_SKUS_SHEET_ID", PROD_SKUS_SHEET_ID).strip(),
            resultados_sheet_id=os.environ.get(
                "CDP_STOKAI_RESULTADOS_SHEET_ID",
                PROD_RESULTADOS_SHEET_ID,
            ).strip(),
        )

    raise ValueError(f"unsupported target: {target}")


def dest_for(kind: str, cfg: TargetConfig) -> Path:
    return WORKFLOW_DIR / cfg.dir_name / f"{cfg.file_prefix}_cdp_{kind}.json"


def workflow_name(kind: str, cfg: TargetConfig) -> str:
    return f"{cfg.workflow_prefix}cdp_{kind}"


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


def _patch_telegram_credentials(wf: dict[str, Any], cfg: TargetConfig) -> None:
    for node in wf.get("nodes", []):
        credentials = node.get("credentials")
        if not isinstance(credentials, dict):
            continue
        telegram = credentials.get("telegramApi")
        if not isinstance(telegram, dict):
            continue
        telegram["id"] = cfg.telegram_credential_id
        telegram["name"] = cfg.telegram_credential_name


def _patch_sheet_ids(wf: dict[str, Any], cfg: TargetConfig) -> None:
    mapping = {
        PROD_SKUS_SHEET_ID: cfg.skus_sheet_id,
        PROD_RESULTADOS_SHEET_ID: cfg.resultados_sheet_id,
    }
    patched = _replace_strings(wf, mapping)
    wf.clear()
    wf.update(patched)


def _regenerate_webhook_ids(wf: dict[str, Any]) -> None:
    """Target copies must not reuse prod webhookIds (n8n activate returns 409)."""
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


def _patch_scraper_secret_check(wf: dict[str, Any]) -> None:
    secret_expr = (
        "(/^DEV\\s*-/i.test($workflow.name || '') ? "
        "($env.CDP_DEV_CALLBACK_WEBHOOK_SECRET || $env.CDP_CALLBACK_WEBHOOK_SECRET || "
        "$env.CALLBACK_WEBHOOK_SECRET || $env.N8N_WEBHOOK_SECRET || '') : "
        "(/^STOKAI\\s*-/i.test($workflow.name || '') ? "
        "($env.CDP_STOKAI_CALLBACK_WEBHOOK_SECRET || $env.CDP_CALLBACK_WEBHOOK_SECRET || "
        "$env.CALLBACK_WEBHOOK_SECRET || $env.N8N_WEBHOOK_SECRET || '') : "
        "($env.CDP_CALLBACK_WEBHOOK_SECRET || $env.CALLBACK_WEBHOOK_SECRET || "
        "$env.N8N_WEBHOOK_SECRET || '')))"
    )
    for node in wf.get("nodes", []):
        if node.get("name") != "🔐 Verificar Webhook Secret":
            continue
        conditions = node.get("parameters", {}).get("conditions", {}).get("conditions", [])
        for condition in conditions:
            if condition.get("id") != "verify-secret":
                continue
            condition["leftValue"] = (
                "={{ ((" + secret_expr + ").trim()) ? "
                "(($json.headers['x-webhook-secret'] || $json.headers['X-Webhook-Secret'] || '').trim()) "
                ": '__missing_webhook_secret__' }}"
            )
            condition["rightValue"] = "={{ (" + secret_expr + ").trim() }}"


STOKAPI_SECRET_CHECK_JS = r"""function readEnv(name) {
  try {
    const fromN8n = typeof $env !== 'undefined' ? $env[name] : undefined;
    if (fromN8n !== undefined && fromN8n !== null && String(fromN8n).trim()) {
      return String(fromN8n).trim();
    }
  } catch (e) {}
  try {
    if (typeof process !== 'undefined' && process.env && process.env[name]) {
      return String(process.env[name]).trim();
    }
  } catch (e) {}
  return '';
}
function workflowName() {
  try {
    if (typeof $workflow !== 'undefined' && $workflow && $workflow.name) {
      return String($workflow.name).trim();
    }
  } catch (e) {}
  return '';
}
function workflowTarget() {
  const name = workflowName();
  if (/^DEV\s*-/i.test(name)) return 'dev';
  if (/^STOKAI\s*-/i.test(name)) return 'stokai';
  return 'prod';
}
const wh = $input.first().json;
const got = String(
  wh.headers?.['x-webhook-secret'] || wh.headers?.['X-Webhook-Secret'] || ''
).trim();
const target = workflowTarget();
const want = target === 'dev'
  ? readEnv('CDP_DEV_MUVSTOK_CALLBACK_WEBHOOK_SECRET') ||
    readEnv('CDP_MUVSTOK_CALLBACK_WEBHOOK_SECRET') ||
    readEnv('CALLBACK_WEBHOOK_SECRET') ||
    readEnv('CDP_CALLBACK_WEBHOOK_SECRET') ||
    readEnv('N8N_WEBHOOK_SECRET') ||
    ''
  : target === 'stokai'
    ? readEnv('CDP_STOKAI_MUVSTOK_CALLBACK_WEBHOOK_SECRET') ||
      readEnv('CDP_MUVSTOK_CALLBACK_WEBHOOK_SECRET') ||
      readEnv('CALLBACK_WEBHOOK_SECRET') ||
      readEnv('CDP_CALLBACK_WEBHOOK_SECRET') ||
      readEnv('N8N_WEBHOOK_SECRET') ||
      ''
    : readEnv('CDP_MUVSTOK_CALLBACK_WEBHOOK_SECRET') ||
      readEnv('CALLBACK_WEBHOOK_SECRET') ||
      readEnv('CDP_CALLBACK_WEBHOOK_SECRET') ||
      readEnv('N8N_WEBHOOK_SECRET') ||
      '';
return [{ json: { ...wh, authorized: !!want && got === want, secret_configured: !!want, secret_received: !!got } }];
"""


def _patch_stokapi_secret_check(wf: dict[str, Any]) -> None:
    for node in wf.get("nodes", []):
        if node.get("name") == "🔐 Verificar Webhook Secret":
            node.setdefault("parameters", {})["jsCode"] = STOKAPI_SECRET_CHECK_JS


def _patch_progress_schedule(wf: dict[str, Any], cfg: TargetConfig) -> None:
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
            f"={{{{ Number($env.{cfg.progress_interval_env} || $env.CDP_PROGRESS_INTERVAL_MIN || 10) }}}}"
        )


def _strip_import_metadata(wf: dict[str, Any]) -> None:
    for key in ("id", "versionId", "meta", "pinData", "tags"):
        wf.pop(key, None)


def transform_workflow(wf: dict[str, Any], *, kind: str, cfg: TargetConfig) -> dict[str, Any]:
    out = copy.deepcopy(wf)
    out["name"] = workflow_name(kind, cfg)
    _strip_import_metadata(out)
    _patch_telegram_credentials(out, cfg)
    _patch_sheet_ids(out, cfg)

    if kind == "router":
        _regenerate_webhook_ids(out)
        if cfg.disable_router_non_telegram_triggers:
            _disable_router_non_telegram_triggers(out)
    elif kind == "scraper":
        _patch_receiver_webhooks(out, old_path="scraper-result", new_path=cfg.scraper_webhook_path)
        _patch_scraper_secret_check(out)
    elif kind == "stokapi":
        _patch_receiver_webhooks(out, old_path="muvstok-result", new_path=cfg.stokapi_webhook_path)
        _patch_stokapi_secret_check(out)
    elif kind == "progress":
        _patch_progress_schedule(out, cfg)
    elif kind == "notifier":
        _patch_receiver_webhooks(out, old_path="cdp-notifier", new_path=cfg.notifier_webhook_path)
        if cfg.disable_notifier_gmail:
            _disable_notifier_gmail(out)
    return out


def audit_workflow(wf: dict[str, Any], *, kind: str, cfg: TargetConfig) -> list[str]:
    problems: list[str] = []
    blob = json.dumps(wf, ensure_ascii=False)

    if cfg.forbid_prod_telegram and PROD_TELEGRAM_CREDENTIAL_ID in blob:
        problems.append(f"{kind}: production Telegram credential id remains in {cfg.key.upper()} JSON")
    if cfg.forbid_prod_sheets and PROD_SKUS_SHEET_ID in blob:
        problems.append(f"{kind}: production SKUs sheet id remains in {cfg.key.upper()} JSON")
    if cfg.forbid_prod_sheets and PROD_RESULTADOS_SHEET_ID in blob:
        problems.append(f"{kind}: production resultados sheet id remains in {cfg.key.upper()} JSON")

    expected_paths = {
        "scraper": cfg.scraper_webhook_path,
        "stokapi": cfg.stokapi_webhook_path,
        "notifier": cfg.notifier_webhook_path,
    }
    old_paths = {
        "scraper": "scraper-result",
        "stokapi": "muvstok-result",
        "notifier": "cdp-notifier",
    }
    if kind in expected_paths:
        found_expected = False
        for node in wf.get("nodes", []):
            if node.get("type") != "n8n-nodes-base.webhook":
                continue
            path = node.get("parameters", {}).get("path")
            if path == old_paths[kind]:
                problems.append(f"{kind}: production webhook path remains in {cfg.key.upper()} JSON")
            if path == expected_paths[kind]:
                found_expected = True
        if not found_expected:
            problems.append(f"{kind}: missing expected webhook path {expected_paths[kind]}")

    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", choices=("dev", "stokai"), default="dev")
    parser.add_argument(
        "--require-telegram-credential",
        action="store_true",
        help="For DEV, exit with code 1 when N8N_DEV_TELEGRAM_CREDENTIAL_ID is unset.",
    )
    args = parser.parse_args(argv)
    cfg = target_config(args.target)

    if args.require_telegram_credential and cfg.key == "dev":
        env_value = os.environ.get("N8N_DEV_TELEGRAM_CREDENTIAL_ID", "").strip()
        if not env_value:
            print(
                "N8N_DEV_TELEGRAM_CREDENTIAL_ID is required for import-n8n-dev "
                "(create or select the dev-cdp-bot Telegram credential in n8n first).",
                file=sys.stderr,
            )
            return 1

    target_dir = WORKFLOW_DIR / cfg.dir_name
    target_dir.mkdir(parents=True, exist_ok=True)
    failures: list[str] = []

    for kind in KINDS:
        src = SOURCE_BY_KIND[kind]
        dest = dest_for(kind, cfg)

        if not src.is_file():
            failures.append(f"{kind}: missing source workflow {src}")
            continue

        wf = json.loads(src.read_text(encoding="utf-8"))
        target_wf = transform_workflow(wf, kind=kind, cfg=cfg)
        problems = audit_workflow(target_wf, kind=kind, cfg=cfg)
        if problems:
            failures.extend(problems)
            continue

        dest.write_text(json.dumps(target_wf, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {dest.relative_to(REPO_ROOT)} ({len(target_wf.get('nodes', []))} nodes)")

    if failures:
        print(f"{cfg.key.upper()} workflow generation failed:", file=sys.stderr)
        for problem in failures:
            print(f"  - {problem}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
