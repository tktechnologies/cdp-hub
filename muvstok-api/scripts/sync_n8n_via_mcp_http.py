#!/usr/bin/env python3
"""Push Muvstok n8n SDK workflows via production MCP HTTP (uses ~/.cursor/mcp.json auth)."""
from __future__ import annotations

import json
import pathlib
import sys
import urllib.error
import urllib.request

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
MCP_JSON = pathlib.Path.home() / ".cursor" / "mcp.json"
MCP_URL = "https://automacao.tktechnologies.com.br/mcp-server/http"

WORKFLOWS = [
    ("stokapi", REPO_ROOT / "n8n/sdk/cdp_stokapi.workflow.ts", "t160mzGPYYlJcrjZ"),
]


def mcp_auth_header() -> str:
    data = json.loads(MCP_JSON.read_text(encoding="utf-8"))
    return data["mcpServers"]["n8n-mcp"]["env"]["N8N_MCP_AUTH_HEADER"]


def mcp_call(tool: str, arguments: dict) -> dict:
    body = json.dumps(
        {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": tool, "arguments": arguments}}
    ).encode()
    req = urllib.request.Request(
        MCP_URL,
        data=body,
        method="POST",
        headers={
            "Authorization": mcp_auth_header(),
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        },
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        raw = resp.read().decode()
    if raw.strip().startswith("{"):
        return json.loads(raw)
    last = ""
    for line in raw.splitlines():
        if line.startswith("data:"):
            last = line[5:].strip()
    return json.loads(last) if last else {"raw": raw[:800]}


def parse_structured(data: dict) -> dict:
    sc = data.get("structuredContent")
    if isinstance(sc, dict):
        return sc
    content = data.get("result", {}).get("content") or []
    for item in content:
        if item.get("type") == "text":
            try:
                return json.loads(item["text"])
            except json.JSONDecodeError:
                continue
    return {}


def main() -> int:
    auth = mcp_auth_header()
    if not auth:
        print("Missing N8N_MCP_AUTH_HEADER in ~/.cursor/mcp.json", file=sys.stderr)
        return 1

    for name, path, workflow_id in WORKFLOWS:
        code = path.read_text(encoding="utf-8")
        v = parse_structured(mcp_call("validate_workflow", {"code": code}))
        if not v.get("valid"):
            print(f"[{name}] validate failed: {v}", file=sys.stderr)
            return 1
        print(f"[{name}] validate OK nodes={v.get('nodeCount')}")

        u = parse_structured(
            mcp_call(
                "update_workflow",
                {"workflowId": workflow_id, "code": code, "description": f"API Diversos {name} sync"},
            )
        )
        print(f"[{name}] update OK id={u.get('workflowId')} url={u.get('url', '')}")

        p = parse_structured(mcp_call("publish_workflow", {"workflowId": workflow_id}))
        if p.get("success"):
            print(f"[{name}] publish OK version={p.get('activeVersionId')}")
        else:
            print(f"[{name}] publish skipped: {p.get('error', p)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
