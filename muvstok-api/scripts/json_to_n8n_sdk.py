#!/usr/bin/env python3
"""Convert repo n8n workflow JSON into n8n Workflow SDK TypeScript for MCP update."""
from __future__ import annotations

import json
import sys
from pathlib import Path


def esc_js(s: str) -> str:
    return json.dumps(s, ensure_ascii=False)


def node_block(node: dict) -> str:
    params = json.dumps(node.get("parameters", {}), ensure_ascii=False)
    creds = ""
    if node.get("credentials"):
        creds = f", credentials: {json.dumps(node['credentials'], ensure_ascii=False)}"
    webhook = ""
    if node.get("webhookId"):
        webhook = f", webhookId: {json.dumps(node['webhookId'])}"
    retry = ""
    if node.get("retryOnFail"):
        retry = ", retryOnFail: true"
        if node.get("maxTries"):
            retry += f", maxTries: {node['maxTries']}"
        if node.get("waitBetweenTries"):
            retry += f", waitBetweenTries: {node['waitBetweenTries']}"
    return f"""const {safe_id(node['name'])} = node({{
  type: {json.dumps(node['type'])},
  version: {node.get('typeVersion', 1)},
  config: {{
    name: {json.dumps(node['name'])},
    parameters: {params}{creds}{webhook}{retry}
  }}
}});"""


def safe_id(name: str) -> str:
    out = "".join(ch if ch.isalnum() else "_" for ch in name)
    if out[0].isdigit():
        out = "n_" + out
    return out[:60] or "node"


def build_connections(connections: dict) -> list[str]:
    lines: list[str] = []
    for _source, conn in connections.items():
        mains = conn.get("main") or []
        for out_idx, targets in enumerate(mains):
            for t in targets:
                tid = safe_id(t["node"])
                if out_idx == 0:
                    lines.append(f".to({tid})")
                else:
                    # false branch etc. handled separately in workflow builder
                    pass
    return lines


def main() -> int:
    if len(sys.argv) < 4:
        print("usage: json_to_n8n_sdk.py <workflow.json> <workflowId> <exportName>", file=sys.stderr)
        return 1
    path = Path(sys.argv[1])
    wf_id = sys.argv[2]
    export_name = sys.argv[3]
    data = json.loads(path.read_text(encoding="utf-8"))
    wf_name = data.get("name", export_name)

    nodes = data["nodes"]
    connections = data["connections"]

    # Map name -> var
    name_to_var = {n["name"]: safe_id(n["name"]) for n in nodes}

    parts = [
        "import { workflow, node, trigger, ifElse, expr } from '@n8n/workflow-sdk';",
        "",
    ]
    for n in nodes:
        if n["type"] == "n8n-nodes-base.manualTrigger":
            parts.append(
                f"const {name_to_var[n['name']]} = trigger({{ type: 'n8n-nodes-base.manualTrigger', version: 1, config: {{ name: {json.dumps(n['name'])} }} }});"
            )
        elif n["type"] == "n8n-nodes-base.webhook":
            p = json.dumps(n.get("parameters", {}), ensure_ascii=False)
            parts.append(
                f"const {name_to_var[n['name']]} = trigger({{ type: 'n8n-nodes-base.webhook', version: {n.get('typeVersion',2)}, config: {{ name: {json.dumps(n['name'])}, parameters: {p} }} }});"
            )
        elif n["type"] == "n8n-nodes-base.if":
            p = json.dumps(n.get("parameters", {}), ensure_ascii=False)
            parts.append(
                f"const {name_to_var[n['name']]} = ifElse({{ version: {n.get('typeVersion',2)}, config: {{ name: {json.dumps(n['name'])}, parameters: {p} }} }});"
            )
        else:
            parts.append(node_block(n))

    parts.append("")
    parts.append(f"export default workflow({json.dumps(wf_id)}, {json.dumps(wf_name)})")

    # naive linear chain from connections - for complex graphs use manual SDK
    triggers = [n for n in nodes if "Trigger" in n["name"] or n["type"].endswith("webhook")]
    if triggers:
        start = triggers[0]["name"]
        parts.append(f"  .add({name_to_var[start]})")

    # emit .to for first outgoing only; fan-out duplicated via repeated .to on same source in SDK
    emitted: set[tuple[str, str]] = set()
    for source, conn in connections.items():
        sid = name_to_var[source]
        for branch_idx, targets in enumerate(conn.get("main") or []):
            for t in targets:
                tid = name_to_var[t["node"]]
                key = (source, t["node"])
                if key in emitted:
                    continue
                emitted.add(key)
                if branch_idx == 0 and len(conn.get("main") or []) == 1:
                    parts.append(f"  .to({sid}.to({tid}))")
                elif branch_idx == 0:
                    parts.append(f"  .to({sid}.to({tid}))")
                else:
                    parts.append(f"  .to({sid}.onFalse({tid}))")

    parts.append(";")
    sys.stdout.write("\n".join(parts))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
