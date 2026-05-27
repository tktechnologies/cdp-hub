#!/usr/bin/env python3
"""Add CDP progress visibility nodes to cdp_router.json."""
from __future__ import annotations

import json
import pathlib
import uuid

ROOT = pathlib.Path(__file__).resolve().parents[1]
ROUTER = ROOT / "scrapers" / "n8n" / "workflows" / "cdp_router.json"
SHARED = ROOT / "shared" / "n8n"


def new_id() -> str:
    return str(uuid.uuid4())


def load_code(name: str) -> str:
    return (SHARED / name).read_text(encoding="utf-8")


def code_node(name: str, js_file: str, position: list[int]) -> dict:
    return {
        "parameters": {
            "jsCode": load_code(js_file),
            "mode": "runOnceForAllItems",
        },
        "id": new_id(),
        "name": name,
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": position,
    }


def http_get_node(name: str, url_expr: str, key_expr: str, position: list[int]) -> dict:
    return {
        "parameters": {
            "url": url_expr,
            "sendHeaders": True,
            "headerParameters": {
                "parameters": [
                    {"name": "X-API-Key", "value": key_expr},
                ]
            },
            "options": {
                "response": {"response": {"responseFormat": "json"}},
                "timeout": 30000,
            },
        },
        "id": new_id(),
        "name": name,
        "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4.2,
        "position": position,
    }


def telegram_node(name: str, position: list[int]) -> dict:
    return {
        "parameters": {
            "chatId": "={{ $json.chat_id }}",
            "text": "={{ $json.msg_telegram }}",
            "additionalFields": {"parse_mode": "Markdown", "appendAttribution": False},
        },
        "id": new_id(),
        "name": name,
        "type": "n8n-nodes-base.telegram",
        "typeVersion": 1.1,
        "position": position,
        "credentials": {
            "telegramApi": {"id": "UmDqGKD8k0bA10j2", "name": "Telegram account"}
        },
    }


def if_node(name: str, skip_expr: str, position: list[int]) -> dict:
    return {
        "parameters": {
            "conditions": {
                "options": {
                    "caseSensitive": True,
                    "leftValue": "",
                    "typeValidation": "strict",
                    "version": 1,
                },
                "conditions": [
                    {
                        "id": new_id(),
                        "leftValue": skip_expr,
                        "rightValue": True,
                        "operator": {"type": "boolean", "operation": "true"},
                    }
                ],
                "combinator": "and",
            },
            "options": {},
        },
        "id": new_id(),
        "name": name,
        "type": "n8n-nodes-base.if",
        "typeVersion": 2,
        "position": position,
    }


def merge_node(name: str, position: list[int]) -> dict:
    return {
        "parameters": {"mode": "append"},
        "id": new_id(),
        "name": name,
        "type": "n8n-nodes-base.merge",
        "typeVersion": 3,
        "position": position,
    }


def patch() -> None:
    wf = json.loads(ROUTER.read_text(encoding="utf-8"))
    nodes = wf["nodes"]
    conns = wf["connections"]

    # Inject shared telegram router
    for node in nodes:
        if node.get("name") == "📱 Roteador de Comando":
            node["parameters"]["jsCode"] = load_code("router_telegram.js")
            node["notes"] = "v4: adds .status / .andamento / .progresso"

    # Scraper POST body includes metadata for job registry
    for node in nodes:
        if node.get("name") == "🚀 POST → Scraper API (/jobs)":
            node["parameters"]["jsonBody"] = (
                "={{ JSON.stringify({ items: $json.items, sites: $json.sites, "
                "callback_url: $json.callback_url, priority: $json.priority || 5, "
                "batch_group_id: $json.batch_group_id, chat_id: $json.chat_id, "
                "command_route: $json.command_route }) }}"
            )

    # Switch: add status route before ignore
    for node in nodes:
        if node.get("name") != "🔀 Switch Comando (Telegram)":
            continue
        rules = node["parameters"]["rules"]["values"]
        status_rule = {
            "conditions": {
                "options": {
                    "caseSensitive": True,
                    "leftValue": "",
                    "typeValidation": "strict",
                    "version": 1,
                },
                "conditions": [
                    {
                        "id": new_id(),
                        "leftValue": "={{ $json.route }}",
                        "rightValue": "status",
                        "operator": {
                            "type": "string",
                            "operation": "equals",
                            "name": "filter.operator.equals",
                        },
                    }
                ],
                "combinator": "and",
            },
            "renameOutput": True,
            "outputKey": "status",
        }
        # Insert before ignore (second-to-last rule typically)
        insert_at = max(0, len(rules) - 2)
        rules.insert(insert_at, status_rule)
        node["notes"] = (
            "Routes: analisar, sku_*, status, sku_empty, ignore, unauthorized"
        )

    # New nodes
    n_prepare = code_node("📊 Status: preparar", "router_status_prepare.js", [480, 1200])
    n_skip_if = if_node(
        "❓ Status sem consulta?",
        "={{ $json.skip_poll }}",
        [704, 1200],
    )
    n_get_scraper = http_get_node(
        "📊 GET Scraper Job",
        "={{ $json.scraper_job_url }}",
        "={{ $json.scraper_api_key }}",
        [928, 1088],
    )
    n_get_stok = http_get_node(
        "📊 GET StokAPI Job",
        "={{ $json.stokapi_job_url }}",
        "={{ $json.stokapi_api_key }}",
        [928, 1312],
    )
    n_format = code_node("📊 Status: formatar", "router_status.js", [1152, 1200])
    n_tg_status = telegram_node("📱 Telegram: status", [1376, 1200])
    n_tg_skip = telegram_node("📱 Telegram: status (sem run)", [928, 1200])

    n_merge_reg = merge_node("🔀 Merge registrar run", [2224, 3008])
    n_register = code_node("📋 Registrar active run", "router_register_run.js", [2448, 3008])
    n_post_registry = {
        "parameters": {
            "method": "POST",
            "url": "={{ $json.dispatch_runs_url }}",
            "sendHeaders": True,
            "headerParameters": {
                "parameters": [
                    {"name": "Content-Type", "value": "application/json"},
                    {"name": "X-API-Key", "value": "={{ $json.dispatch_runs_api_key }}"},
                ]
            },
            "sendBody": True,
            "specifyBody": "json",
            "jsonBody": (
                "={{ JSON.stringify({ batch_group_id: $json.batch_group_id, "
                "chat_id: $json.chat_id, command_route: $json.command_route, "
                "scraper_job_ids: $json.scraper_job_ids, stokapi_job_id: $json.stokapi_job_id, "
                "total_skus: $json.total_skus, estimated_seconds: $json.estimated_seconds, "
                "dispatched_at: $json.dispatched_at }) }}"
            ),
            "options": {"timeout": 15000},
        },
        "id": new_id(),
        "name": "📋 POST dispatch-runs",
        "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4.2,
        "position": [2672, 3008],
    }

    nodes.extend(
        [
            n_prepare,
            n_skip_if,
            n_get_scraper,
            n_get_stok,
            n_format,
            n_tg_status,
            n_tg_skip,
            n_merge_reg,
            n_register,
            n_post_registry,
        ]
    )

    # Status branch from switch — insert at index 5 (before ignore)
    tg_switch = conns.setdefault("🔀 Switch Comando (Telegram)", {"main": []})
    while len(tg_switch["main"]) < 6:
        tg_switch["main"].append([])
    tg_switch["main"].insert(
        5,
        [{"node": n_prepare["name"], "type": "main", "index": 0}],
    )

    conns[n_prepare["name"]] = {
        "main": [[{"node": n_skip_if["name"], "type": "main", "index": 0}]]
    }
    conns[n_skip_if["name"]] = {
        "main": [
            [{"node": n_tg_skip["name"], "type": "main", "index": 0}],
            [
                {"node": n_get_scraper["name"], "type": "main", "index": 0},
                {"node": n_get_stok["name"], "type": "main", "index": 0},
            ],
        ]
    }
    conns[n_get_scraper["name"]] = {
        "main": [[{"node": n_format["name"], "type": "main", "index": 0}]]
    }
    conns[n_get_stok["name"]] = {
        "main": [[{"node": n_format["name"], "type": "main", "index": 0}]]
    }
    conns[n_format["name"]] = {
        "main": [[{"node": n_tg_status["name"], "type": "main", "index": 0}]]
    }

    # Register run after scraper OK + stokapi accepted
    api_ok = conns.get("✅ API OK?", {}).get("main", [[]])
    if api_ok and api_ok[0]:
        api_ok[0].append({"node": n_merge_reg["name"], "type": "main", "index": 0})

    stok_ok = conns.get("📦 API Diversos job aceito?", {}).get("main", [[]])
    if stok_ok and stok_ok[0]:
        stok_ok[0].append({"node": n_merge_reg["name"], "type": "main", "index": 1})

    conns[n_merge_reg["name"]] = {
        "main": [[{"node": n_register["name"], "type": "main", "index": 0}]]
    }
    reg_main = conns.setdefault(n_register["name"], {"main": [[]]})
    if not reg_main["main"][0]:
        reg_main["main"][0] = []
    reg_main["main"][0].append({"node": n_post_registry["name"], "type": "main", "index": 0})

    wf["nodes"] = nodes
    wf["connections"] = conns
    ROUTER.write_text(json.dumps(wf, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Patched {ROUTER}")


if __name__ == "__main__":
    patch()
