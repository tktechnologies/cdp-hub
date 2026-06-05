#!/usr/bin/env python3
"""Push n8n workflows from repo JSON (REST API) and publish (MCP).

Replaces the code-based MCP update_workflow path, which does not apply graph changes.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
import urllib.error
import urllib.request

MCP_JSON = pathlib.Path.home() / ".cursor" / "mcp.json"
MCP_URL = "https://automacao.tktechnologies.com.br/mcp-server/http"
N8N_API_BASE = "https://automacao.tktechnologies.com.br/api/v1"

# n8n REST PUT rejects some UI-only settings keys (e.g. binaryMode, availableInMCP).
_SETTINGS_ALLOWED = frozenset(
    {
        "executionOrder",
        "timezone",
        "saveDataErrorExecution",
        "saveDataSuccessExecution",
        "saveManualExecutions",
        "saveExecutionProgress",
        "callerPolicy",
        "errorWorkflow",
    }
)


def _workflow_settings(local: dict, remote: dict) -> dict:
    merged = {**(remote.get("settings") or {}), **(local.get("settings") or {})}
    return {k: v for k, v in merged.items() if k in _SETTINGS_ALLOWED}


def _mcp_servers() -> dict:
    if not MCP_JSON.exists():
        return {}
    return json.loads(MCP_JSON.read_text(encoding="utf-8")).get("mcpServers", {})


def mcp_auth_header() -> str:
    header = os.environ.get("N8N_MCP_AUTH_HEADER", "").strip()
    if header:
        return header
    for key in ("user-n8n-mcp", "n8n-mcp"):
        env = _mcp_servers().get(key, {}).get("env", {})
        header = env.get("N8N_MCP_AUTH_HEADER", "")
        if header:
            return header
    return ""


def n8n_api_key() -> str:
    api_key = os.environ.get("N8N_API_KEY", "").strip()
    if api_key:
        return api_key
    for key in ("user-n8n-mcp", "n8n-mcp"):
        env = _mcp_servers().get(key, {}).get("env", {})
        api_key = env.get("N8N_API_KEY", "")
        if api_key:
            return api_key
    return ""


def mcp_url() -> str:
    return os.environ.get("N8N_MCP_URL", MCP_URL).rstrip("/")


def n8n_api_base() -> str:
    return os.environ.get("N8N_API_BASE", N8N_API_BASE).rstrip("/")


def mcp_call(tool: str, arguments: dict) -> dict:
    body = json.dumps(
        {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": tool, "arguments": arguments}}
    ).encode()
    req = urllib.request.Request(
        mcp_url(),
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


def n8n_api_request(method: str, path: str, body: dict | None = None) -> dict:
    url = f"{n8n_api_base()}{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "X-N8N-API-KEY": n8n_api_key(),
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode())


def activate_via_rest(workflow_id: str) -> None:
    try:
        n8n_api_request("POST", f"/workflows/{workflow_id}/activate")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")
        if exc.code == 400 and "already active" in body.lower():
            return
        raise


def validate_sdk(sdk_path: pathlib.Path) -> dict:
    code = sdk_path.read_text(encoding="utf-8")
    return parse_structured(mcp_call("validate_workflow", {"code": code}))


def push_workflow_json(
    workflow_id: str,
    json_path: pathlib.Path,
    *,
    description: str | None = None,
    publish: bool = True,
    validate_sdk_path: pathlib.Path | None = None,
) -> int:
    if validate_sdk_path is not None:
        v = validate_sdk(validate_sdk_path)
        if not v.get("valid"):
            print(f"validate failed: {v}", file=sys.stderr)
            return 1
        print(f"validate OK nodes={v.get('nodeCount')}")

    if not json_path.exists():
        print(f"Missing workflow JSON: {json_path}", file=sys.stderr)
        return 1

    local = json.loads(json_path.read_text(encoding="utf-8"))
    remote = n8n_api_request("GET", f"/workflows/{workflow_id}")

    payload: dict = {
        "name": local.get("name") or remote.get("name"),
        "nodes": local["nodes"],
        "connections": local["connections"],
        "settings": _workflow_settings(local, remote),
    }
    if description:
        payload["description"] = description
    elif remote.get("description"):
        payload["description"] = remote["description"]

    updated = n8n_api_request("PUT", f"/workflows/{workflow_id}", payload)
    node_count = len(updated.get("nodes", []))
    print(f"update OK id={workflow_id} nodes={node_count} (n8n REST API)")

    if publish:
        p = parse_structured(mcp_call("publish_workflow", {"workflowId": workflow_id}))
        if p.get("success"):
            print(f"publish OK version={p.get('activeVersionId')}")
        else:
            error = str(p.get("error", p))
            if "not available in MCP" in error:
                activate_via_rest(workflow_id)
                print(f"publish fallback: activated via REST ({error})")
            else:
                print(f"publish note: {error}", file=sys.stderr)
                return 3

    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Push workflow JSON to n8n and publish via MCP")
    ap.add_argument("--workflow-id", required=True)
    ap.add_argument("--json", type=pathlib.Path, required=True, help="Repo workflow JSON path")
    ap.add_argument("--sdk", type=pathlib.Path, help="Optional SDK for validate_workflow before push")
    ap.add_argument("--description", default="")
    ap.add_argument("--publish", action="store_true", help="Publish after update (default)")
    ap.add_argument("--no-publish", action="store_true")
    args = ap.parse_args()

    if not n8n_api_key():
        print("Missing N8N_API_KEY in environment or ~/.cursor/mcp.json (user-n8n-mcp or n8n-mcp)", file=sys.stderr)
        return 1
    if not mcp_auth_header():
        print("Missing N8N_MCP_AUTH_HEADER in environment or ~/.cursor/mcp.json", file=sys.stderr)
        return 1

    do_publish = args.publish or not args.no_publish
    return push_workflow_json(
        args.workflow_id,
        args.json,
        description=args.description or None,
        publish=do_publish,
        validate_sdk_path=args.sdk,
    )


if __name__ == "__main__":
    raise SystemExit(main())
