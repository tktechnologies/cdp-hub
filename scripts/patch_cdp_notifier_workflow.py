#!/usr/bin/env python3
"""Patch cdp_notifier: CSV email attachment, send guards, delivery hardening."""
from __future__ import annotations

import json
import uuid
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
NOTIFIER_JSON = REPO_ROOT / "n8n" / "workflows" / "cdp_notifier.json"
EXPORT_JS = REPO_ROOT / "n8n" / "lib" / "notifier_job_export.js"

SEND_GUARD_NODE = "❓ Enviar mensagem?"
GET_JOB_NODE = "📥 GET scraper job"
CSV_NODE = "🗂️ Gerar CSV final"
EMAIL_NODE = "📧 Email: resultado final"
FORMATTER_NODE = "📣 Formatar mensagem final"
CHANNEL_NODE = "❓ Canal Telegram?"
PATCH_FINAL_NODE = "📋 PATCH final-notification"
PROD_GMAIL_CREDENTIAL = {"id": "rQesNRyarukVs0N4", "name": "gmail lucas@tktech"}


def _nid() -> str:
    return str(uuid.uuid4())


def _find_node(nodes: list[dict], name: str) -> dict | None:
    for node in nodes:
        if node.get("name") == name:
            return node
    return None


def _link(node: str, index: int = 0) -> dict:
    return {"node": node, "type": "main", "index": index}


def _ensure_send_guard(nodes: list[dict], conns: dict) -> None:
    if _find_node(nodes, SEND_GUARD_NODE) is None:
        nodes.append(
            {
                "parameters": {
                    "conditions": {
                        "options": {
                            "caseSensitive": True,
                            "typeValidation": "strict",
                            "version": 1,
                        },
                        "conditions": [
                            {
                                "id": "send",
                                "leftValue": "={{ $json.skip_send }}",
                                "rightValue": True,
                                "operator": {"type": "boolean", "operation": "false"},
                            }
                        ],
                        "combinator": "and",
                    },
                    "options": {},
                },
                "id": _nid(),
                "name": SEND_GUARD_NODE,
                "type": "n8n-nodes-base.if",
                "typeVersion": 2,
                "position": [1840, 160],
            }
        )
    conns[FORMATTER_NODE] = {"main": [[_link(SEND_GUARD_NODE)]]}
    conns[SEND_GUARD_NODE] = {
        "main": [[_link("❓ Sem destino?")], []],
    }


def _ensure_csv_nodes(nodes: list[dict], conns: dict, export_js: str) -> None:
    get_job = _find_node(nodes, GET_JOB_NODE)
    if get_job is None:
        get_job = {
            "parameters": {
                "method": "GET",
                "url": (
                    "={{ (String(/^DEV\\s*-/.test($workflow.name) ? "
                    "($env.CDP_DEV_SCRAPER_API_BASE || '') : "
                    "(/^STOKAI\\s*-/.test($workflow.name) ? "
                    "($env.CDP_STOKAI_SCRAPER_API_BASE || '') : "
                    "($env.CDP_SCRAPER_API_BASE || $env.MUVSTOK_SCRAPER_API_BASE || '')))"
                    ".trim().replace(/\\/+$/, '')) + '/api/v1/jobs/' + "
                    "encodeURIComponent($('📣 Formatar mensagem final').first().json.scraper_job_id || '') }}"
                ),
                "sendHeaders": True,
                "headerParameters": {
                    "parameters": [
                        {
                            "name": "X-API-Key",
                            "value": (
                                "={{ /^DEV\\s*-/.test($workflow.name) ? "
                                "($env.CDP_DEV_API_KEY || $env.CDP_API_KEY) : "
                                "(/^STOKAI\\s*-/.test($workflow.name) ? "
                                "($env.CDP_STOKAI_API_KEY || '') : "
                                "($env.CDP_API_KEY || $env.MUVSTOK_API_KEY || $env.API_KEY)) }}"
                            ),
                        }
                    ]
                },
                "options": {
                    "response": {"response": {"responseFormat": "json"}},
                    "timeout": 30000,
                },
            },
            "id": _nid(),
            "name": GET_JOB_NODE,
            "type": "n8n-nodes-base.httpRequest",
            "typeVersion": 4.2,
            "position": [2320, 320],
            "continueOnFail": True,
        }
        nodes.append(get_job)

    get_job_params = get_job.setdefault("parameters", {})
    get_job_params["method"] = "GET"
    get_job_params["url"] = (
        "={{ (String(/^DEV\\s*-/.test($workflow.name) ? "
        "($env.CDP_DEV_SCRAPER_API_BASE || '') : "
        "(/^STOKAI\\s*-/.test($workflow.name) ? "
        "($env.CDP_STOKAI_SCRAPER_API_BASE || '') : "
        "($env.CDP_SCRAPER_API_BASE || $env.MUVSTOK_SCRAPER_API_BASE || '')))"
        ".trim().replace(/\\/+$/, '')) + '/api/v1/jobs/' + "
        "encodeURIComponent($('📣 Formatar mensagem final').first().json.scraper_job_id || '') }}"
    )
    get_job_params["sendHeaders"] = True
    get_job_params["headerParameters"] = {
        "parameters": [
            {
                "name": "X-API-Key",
                "value": (
                    "={{ /^DEV\\s*-/.test($workflow.name) ? "
                    "($env.CDP_DEV_API_KEY || $env.CDP_API_KEY) : "
                    "(/^STOKAI\\s*-/.test($workflow.name) ? "
                    "($env.CDP_STOKAI_API_KEY || '') : "
                    "($env.CDP_API_KEY || $env.MUVSTOK_API_KEY || $env.API_KEY)) }}"
                ),
            }
        ]
    }
    get_job_params["options"] = {
        "response": {"response": {"responseFormat": "json"}},
        "timeout": 30000,
    }

    csv_node = _find_node(nodes, CSV_NODE)
    if csv_node is None:
        csv_node = {
            "parameters": {"jsCode": export_js, "mode": "runOnceForAllItems"},
            "id": _nid(),
            "name": CSV_NODE,
            "type": "n8n-nodes-base.code",
            "typeVersion": 2,
            "position": [2560, 320],
            "notes": "Aggregate final email: job-scoped UTF-8 CSV (opens in Excel).",
        }
        nodes.append(csv_node)
    else:
        csv_node["parameters"]["jsCode"] = export_js

    conns[CHANNEL_NODE] = {
        "main": [
            [_link("📱 Telegram: resultado final")],
            [_link(GET_JOB_NODE)],
        ]
    }
    conns[GET_JOB_NODE] = {"main": [[_link(CSV_NODE)]]}
    conns[CSV_NODE] = {"main": [[_link(EMAIL_NODE)]]}


def _patch_email_node(nodes: list[dict]) -> None:
    email = _find_node(nodes, EMAIL_NODE)
    if not email:
        return
    params = email.setdefault("parameters", {})
    params["sendTo"] = "={{ $json.email_to }}"
    params["subject"] = "={{ $json.msg_email_subject }}"
    params["message"] = "={{ $json.msg_email_html }}"
    params["options"] = {"appendAttribution": False}
    params["attachmentsUi"] = {"attachmentsBinary": [{"property": "data"}]}
    email["credentials"] = {"gmailOAuth2": dict(PROD_GMAIL_CREDENTIAL)}
    email.pop("continueOnFail", None)


def _patch_final_notification_node(nodes: list[dict]) -> None:
    patch = _find_node(nodes, PATCH_FINAL_NODE)
    if not patch:
        return

    params = patch.setdefault("parameters", {})
    params["method"] = "PATCH"
    params["url"] = (
        "={{ (String(/^DEV\\s*-/.test($workflow.name) ? "
        "($env.CDP_DEV_SCRAPER_API_BASE || '') : "
        "(/^STOKAI\\s*-/.test($workflow.name) ? "
        "($env.CDP_STOKAI_SCRAPER_API_BASE || '') : "
        "($env.CDP_SCRAPER_API_BASE || $env.MUVSTOK_SCRAPER_API_BASE || '')))"
        ".trim().replace(/\\/+$/, '')) + '/api/v1/dispatch-runs/' + "
        "$('📣 Formatar mensagem final').first().json.run_id + '/final-notification' }}"
    )
    params["sendHeaders"] = True
    params["headerParameters"] = {
        "parameters": [
            {"name": "Content-Type", "value": "application/json"},
            {
                "name": "X-API-Key",
                "value": (
                    "={{ /^DEV\\s*-/.test($workflow.name) ? "
                    "($env.CDP_DEV_API_KEY || $env.CDP_API_KEY) : "
                    "(/^STOKAI\\s*-/.test($workflow.name) ? "
                    "($env.CDP_STOKAI_API_KEY || '') : "
                    "($env.CDP_API_KEY || $env.MUVSTOK_API_KEY || $env.API_KEY)) }}"
                ),
            },
        ]
    }
    params["sendBody"] = True
    params["specifyBody"] = "json"
    params["jsonBody"] = (
        "={{ JSON.stringify({ status: $('📣 Formatar mensagem final').first().json.skipped_no_target "
        "? 'skipped_no_target' : 'sent', final_channel: $('📣 Formatar mensagem final').first().json.reply_channel }) }}"
    )
    params["options"] = {"timeout": 15000}


def main() -> int:
    if not NOTIFIER_JSON.is_file():
        print(f"Missing {NOTIFIER_JSON}", file=__import__("sys").stderr)
        return 1
    export_js = EXPORT_JS.read_text(encoding="utf-8")
    workflow = json.loads(NOTIFIER_JSON.read_text(encoding="utf-8"))
    nodes = workflow.setdefault("nodes", [])
    conns = workflow.setdefault("connections", {})

    _ensure_send_guard(nodes, conns)
    _ensure_csv_nodes(nodes, conns, export_js)
    _patch_email_node(nodes)
    _patch_final_notification_node(nodes)

    NOTIFIER_JSON.write_text(json.dumps(workflow, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Patched {NOTIFIER_JSON.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
