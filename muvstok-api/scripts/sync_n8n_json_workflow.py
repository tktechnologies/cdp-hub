#!/usr/bin/env python3
"""Push full workflow JSON to n8n REST API (preserves all nodes and connections)."""
from __future__ import annotations

import json
import pathlib
import sys
import urllib.error
import urllib.request

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
MCP_JSON = pathlib.Path.home() / ".cursor" / "mcp.json"
N8N_BASE = "https://automacao.tktechnologies.com.br/api/v1"

WORKFLOW_ID = "t160mzGPYYlJcrjZ"
WORKFLOW_JSON = REPO_ROOT / "n8n/workflows/cdp_stokapi.json"


def api_key() -> str:
    data = json.loads(MCP_JSON.read_text(encoding="utf-8"))
    return data["mcpServers"]["n8n-mcp"]["env"]["N8N_API_KEY"]


def api_request(method: str, path: str, body: dict | None = None) -> dict:
    url = f"{N8N_BASE}{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "X-N8N-API-KEY": api_key(),
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode())


def main() -> int:
    if not WORKFLOW_JSON.exists():
        print(f"Missing {WORKFLOW_JSON}", file=sys.stderr)
        return 1

    local = json.loads(WORKFLOW_JSON.read_text(encoding="utf-8"))
    remote = api_request("GET", f"/workflows/{WORKFLOW_ID}")

    payload = {
        "name": local.get("name") or remote.get("name") or "cdp_stokapi",
        "nodes": local["nodes"],
        "connections": local["connections"],
        "settings": local.get("settings") or remote.get("settings") or {},
    }
    if remote.get("description"):
        payload["description"] = remote["description"]

    updated = api_request("PUT", f"/workflows/{WORKFLOW_ID}", payload)
    node_count = len(updated.get("nodes", []))
    print(f"Updated workflow {WORKFLOW_ID} nodes={node_count}")

    # Activate published version
    try:
        api_request("POST", f"/workflows/{WORKFLOW_ID}/activate")
        print("Activated workflow")
    except urllib.error.HTTPError as exc:
        print(f"Activate skipped ({exc.code}): {exc.read().decode()[:200]}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
