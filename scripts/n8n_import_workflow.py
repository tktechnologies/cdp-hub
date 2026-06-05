#!/usr/bin/env python3
"""Create an n8n workflow from repo JSON (first import). Prints workflow ID on success."""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

# Reuse credentials from n8n_publish
from n8n_publish import n8n_api_key, n8n_api_request, mcp_auth_header, mcp_call, parse_structured


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", type=pathlib.Path, required=True)
    ap.add_argument("--publish", action="store_true", help="Activate via MCP publish_workflow")
    args = ap.parse_args()

    if not n8n_api_key() or not mcp_auth_header():
        print("Configure N8N_API_KEY and N8N_MCP_AUTH_HEADER in env or ~/.cursor/mcp.json", file=sys.stderr)
        return 1

    local = json.loads(args.json.read_text(encoding="utf-8"))
    payload = {
        "name": local["name"],
        "nodes": local["nodes"],
        "connections": local["connections"],
        "settings": local.get("settings") or {},
    }
    if local.get("description"):
        payload["description"] = local["description"]

    created = n8n_api_request("POST", "/workflows", payload)
    wf_id = created["id"]
    print(wf_id)

    if args.publish:
        p = parse_structured(mcp_call("publish_workflow", {"workflowId": wf_id}))
        if p.get("success"):
            print(f"published version={p.get('activeVersionId')}", file=sys.stderr)
        else:
            # New workflows may lack MCP access; activate via REST instead.
            n8n_api_request("POST", f"/workflows/{wf_id}/activate")
            print(f"MCP publish skipped; activated via REST ({p.get('error', 'unknown')})", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
