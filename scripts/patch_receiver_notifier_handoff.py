#!/usr/bin/env python3
"""Ensure aggregate notifier handoff nodes exist on scraper/stokapi receivers."""
from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRAPER_JSON = REPO_ROOT / "n8n" / "workflows" / "cdp_scraper.json"
STOKAPI_JSON = REPO_ROOT / "n8n" / "workflows" / "cdp_stokapi.json"
HANDOFF_NODE = "📣 Preparar handoff notifier"
POST_NODE = "📤 POST cdp-notifier"


def _nid() -> str:
    return str(uuid.uuid4())


def _find_node(nodes: list[dict], name: str) -> dict | None:
    for node in nodes:
        if node.get("name") == name:
            return node
    return None


def _has_handoff(wf: dict) -> bool:
    return _find_node(wf.get("nodes", []), HANDOFF_NODE) is not None


def _handoff_js_from(wf: dict) -> str | None:
    node = _find_node(wf.get("nodes", []), HANDOFF_NODE)
    if node is None:
        return None
    return node.get("parameters", {}).get("jsCode")


def _ensure_handoff_nodes(wf: dict, *, handoff_js: str, after_node: str) -> None:
    nodes = wf.setdefault("nodes", [])
    conns = wf.setdefault("connections", {})

    prep = _find_node(nodes, HANDOFF_NODE)
    if prep is None:
        prep = {
            "parameters": {"jsCode": handoff_js, "mode": "runOnceForAllItems"},
            "id": _nid(),
            "name": HANDOFF_NODE,
            "type": "n8n-nodes-base.code",
            "typeVersion": 2,
            "position": [3200, 400],
            "notes": "Aggregate delivery: POST compact summary to cdp_notifier.",
        }
        post = {
            "parameters": {
                "method": "POST",
                "url": "={{ $json.notifier_url }}",
                "sendBody": True,
                "specifyBody": "json",
                "jsonBody": "={{ JSON.stringify($json.handoff_body) }}",
                "options": {"timeout": 30000},
            },
            "id": _nid(),
            "name": POST_NODE,
            "type": "n8n-nodes-base.httpRequest",
            "typeVersion": 4.2,
            "position": [3440, 400],
            "continueOnFail": True,
        }
        nodes.extend([prep, post])
    else:
        prep["parameters"]["jsCode"] = handoff_js

    old_targets = [
        link["node"] for link in conns.get(after_node, {}).get("main", [[]])[0]
    ]
    conns[after_node] = {"main": [[{"node": HANDOFF_NODE, "type": "main", "index": 0}]]}
    conns[HANDOFF_NODE] = {"main": [[{"node": POST_NODE, "type": "main", "index": 0}]]}
    conns[POST_NODE] = {
        "main": [[{"node": name, "type": "main", "index": 0} for name in old_targets]]
    }


def main() -> int:
    scraper = json.loads(SCRAPER_JSON.read_text(encoding="utf-8"))
    stokapi = json.loads(STOKAPI_JSON.read_text(encoding="utf-8"))

    if _has_handoff(scraper) and _has_handoff(stokapi):
        print("OK: receiver notifier handoff nodes present")
        return 0

    scraper_js = _handoff_js_from(scraper)
    stokapi_js = _handoff_js_from(stokapi)
    if not scraper_js and stokapi_js:
        scraper_js = stokapi_js.replace("cdp_stokapi", "cdp_scraper").replace(
            "source: 'stokapi'", "source: 'scraper'"
        )
    if not stokapi_js and scraper_js:
        stokapi_js = scraper_js.replace("cdp_scraper", "cdp_stokapi").replace(
            "source: 'scraper'", "source: 'stokapi'"
        )
    if not scraper_js or not stokapi_js:
        print(
            "Cannot patch notifier handoff: no embedded handoff Code found in receiver workflows.",
            file=sys.stderr,
        )
        return 1

    _ensure_handoff_nodes(
        scraper,
        handoff_js=scraper_js,
        after_node="📋 Salvar → CDP_Resultados (Resumo)",
    )
    SCRAPER_JSON.write_text(json.dumps(scraper, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Patched {SCRAPER_JSON.relative_to(REPO_ROOT)}")

    resumo_name = "📋 Salvar → CDP_Resultados (Resumo)"
    if _find_node(stokapi.get("nodes", []), resumo_name) is None:
        resumo_name = next(
            (
                node["name"]
                for node in stokapi.get("nodes", [])
                if "Resumo" in node.get("name", "") and "Salvar" in node.get("name", "")
            ),
            resumo_name,
        )

    _ensure_handoff_nodes(stokapi, handoff_js=stokapi_js, after_node=resumo_name)
    STOKAPI_JSON.write_text(json.dumps(stokapi, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Patched {STOKAPI_JSON.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
