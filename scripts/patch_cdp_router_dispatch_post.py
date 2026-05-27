#!/usr/bin/env python3
"""Add POST dispatch-runs node and wire StokAPI success to Registrar Execução."""
from __future__ import annotations

import json
import pathlib
import uuid

ROUTER = pathlib.Path(__file__).resolve().parents[1] / "scrapers" / "n8n" / "workflows" / "cdp_router.json"


def main() -> None:
    wf = json.loads(ROUTER.read_text(encoding="utf-8"))
    nodes = wf["nodes"]
    conns = wf["connections"]

    post_name = "📋 POST dispatch-runs"
    if not any(n.get("name") == post_name for n in nodes):
        nodes.append(
            {
                "parameters": {
                    "method": "POST",
                    "url": "={{ $json.dispatch_runs_url }}",
                    "sendHeaders": True,
                    "headerParameters": {
                        "parameters": [
                            {"name": "Content-Type", "value": "application/json"},
                            {
                                "name": "X-API-Key",
                                "value": "={{ $json.dispatch_runs_api_key }}",
                            },
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
                "id": str(uuid.uuid4()),
                "name": post_name,
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 4.2,
                "position": [2448, 2528],
                "continueOnFail": True,
            }
        )

    reg = conns.setdefault("📊 Registrar Execução", {"main": [[]]})
    if reg["main"][0] and not any(
        link.get("node") == post_name for link in reg["main"][0]
    ):
        reg["main"][0].append({"node": post_name, "type": "main", "index": 0})

    stok = conns.get("📦 API Diversos job aceito?", {}).get("main", [[], []])
    if stok and stok[0] is not None:
        if not any(link.get("node") == "📊 Registrar Execução" for link in stok[0]):
            stok[0].append({"node": "📊 Registrar Execução", "type": "main", "index": 0})

    for node in nodes:
        if node.get("name") == "🚀 POST → Scraper API (/jobs)":
            node["parameters"]["jsonBody"] = (
                "={{ JSON.stringify({ items: $json.items, sites: $json.sites, "
                "callback_url: $json.callback_url, priority: $json.priority || 5, "
                "batch_group_id: $json.batch_group_id, chat_id: $json.chat_id, "
                "command_route: $json.command_route }) }}"
            )

    wf["nodes"] = nodes
    wf["connections"] = conns
    ROUTER.write_text(json.dumps(wf, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Patched {ROUTER}")


if __name__ == "__main__":
    main()
