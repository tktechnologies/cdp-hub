#!/usr/bin/env python3
"""Validate + update + publish one workflow via production n8n MCP HTTP."""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import urllib.error
import urllib.request

MCP_JSON = pathlib.Path.home() / ".cursor" / "mcp.json"
MCP_URL = "https://automacao.tktechnologies.com.br/mcp-server/http"


def mcp_auth_header() -> str:
    data = json.loads(MCP_JSON.read_text(encoding="utf-8"))
    servers = data.get("mcpServers", {})
    for key in ("user-n8n-mcp", "n8n-mcp"):
        if key in servers:
            return servers[key].get("env", {}).get("N8N_MCP_AUTH_HEADER", "")
    return ""


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
    with urllib.request.urlopen(req, timeout=300) as resp:
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


def push(workflow_id: str, sdk_path: pathlib.Path, description: str, publish: bool) -> int:
    code = sdk_path.read_text(encoding="utf-8")
    v = parse_structured(mcp_call("validate_workflow", {"code": code}))
    if not v.get("valid"):
        print(f"validate failed: {v}", file=sys.stderr)
        return 1
    print(f"validate OK nodes={v.get('nodeCount')}")

    u = parse_structured(
        mcp_call("update_workflow", {"workflowId": workflow_id, "code": code, "description": description})
    )
    # The MCP `update_workflow` tool only accepts `operations` (additionalProperties:false);
    # a `code` payload is rejected and applies NOTHING while still returning 200. Detect the
    # no-op so we never again "publish" a stale graph and think it worked.
    if not (u.get("workflowId") or u.get("appliedOperations")):
        print(
            "ERROR: update_workflow did not apply (code-based update is a no-op on this MCP).\n"
            "       The live graph was NOT changed. Apply structural changes via\n"
            "       update_workflow `operations` + publish_workflow instead, or rewrite this\n"
            f"       pusher to diff→operations. Raw response: {u}",
            file=sys.stderr,
        )
        return 2
    print(f"update OK id={u.get('workflowId')} url={u.get('url', '')}")

    if publish:
        p = parse_structured(mcp_call("publish_workflow", {"workflowId": workflow_id}))
        if p.get("success"):
            print(f"publish OK version={p.get('activeVersionId')}")
        else:
            print(f"publish note: {p.get('error', p)}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workflow-id", required=True)
    ap.add_argument("--sdk", type=pathlib.Path, required=True)
    ap.add_argument("--description", default="CDP workflow sync")
    ap.add_argument("--publish", action="store_true", help="Publish after update")
    ap.add_argument("--no-publish", action="store_true")
    args = ap.parse_args()
    if not mcp_auth_header():
        print("Missing N8N_MCP_AUTH_HEADER in ~/.cursor/mcp.json", file=sys.stderr)
        return 1
    do_publish = args.publish or not args.no_publish
    return push(args.workflow_id, args.sdk, args.description, publish=do_publish)


if __name__ == "__main__":
    raise SystemExit(main())
