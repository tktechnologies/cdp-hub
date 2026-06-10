#!/usr/bin/env python3
"""Align cdp_skus Google Sheets node tab refs and ensure notifier writes NOTIFICADO."""
from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from cdp_skus_sheet_columns import patch_status_columns, sheet_column_id, sheet_display_name  # noqa: E402
WORKFLOWS = [
    ROOT / "n8n" / "workflows" / "cdp_router.json",
    ROOT / "n8n" / "workflows" / "cdp_scraper.json",
    ROOT / "n8n" / "workflows" / "cdp_stokapi.json",
    ROOT / "n8n" / "workflows" / "cdp_notifier.json",
]

CDP_SKUS_DOC_ID = "1IGhsIhrwlnMaCduR-W-eIi9O4mMO2pPYjE-tefgIPII"
CDP_SKUS_GID = 843035952
CDP_SKUS_TAB = "SKUs"
CDP_SKUS_SHEET_URL = (
    f"https://docs.google.com/spreadsheets/d/{CDP_SKUS_DOC_ID}/edit#gid={CDP_SKUS_GID}"
)
SHEETS_CREDENTIALS = {
    "googleSheetsOAuth2Api": {
        "id": "ep05fPlF3xggWhWc",
        "name": "gcp sheets lucas@tktech",
    }
}

NOTIFIER_MARK_NODE = "✅ Marcar NOTIFICADO → CDP_SKUs"
NOTIFIER_EXPAND_NODE = "🔧 Expandir NOTIFICADO"
NOTIFIER_READ_NODE = "📄 Ler CDP_SKUs (NOTIFICADO)"
NOTIFIER_REMAP_NODE = "🧭 Mapear NOTIFICADO por row"
SHARED_SRC = ROOT / "n8n" / "src"


def cdp_skus_sheet_ref() -> dict:
    return {
        "__rl": True,
        "value": CDP_SKUS_GID,
        "mode": "list",
        "cachedResultName": CDP_SKUS_TAB,
        "cachedResultUrl": CDP_SKUS_SHEET_URL,
    }


def is_cdp_skus_document(document_id: object) -> bool:
    if not isinstance(document_id, dict):
        return False
    return str(document_id.get("value", "")).strip() == CDP_SKUS_DOC_ID


def patch_sheet_name(node: dict) -> bool:
    if node.get("type") != "n8n-nodes-base.googleSheets":
        return False
    params = node.get("parameters", {})
    if not is_cdp_skus_document(params.get("documentId")):
        return False
    changed = False
    if params.get("sheetName") != cdp_skus_sheet_ref():
        changed = True
    params["sheetName"] = cdp_skus_sheet_ref()
    columns = params.get("columns")
    if isinstance(columns, dict) and patch_status_columns(columns):
        changed = True
    return changed


def notifier_mark_node(expand_node: dict) -> dict:
    base_pos = expand_node.get("position", [2560, 360])
    return {
        "parameters": {
            "operation": "update",
            "documentId": {
                "__rl": True,
                "value": CDP_SKUS_DOC_ID,
                "mode": "list",
                "cachedResultName": "cdp_skus",
                "cachedResultUrl": (
                    f"https://docs.google.com/spreadsheets/d/{CDP_SKUS_DOC_ID}/edit?usp=drivesdk"
                ),
            },
            "sheetName": cdp_skus_sheet_ref(),
            "columns": {
                "mappingMode": "defineBelow",
                "value": {
                    "row_number": "={{ $json.row_number }}",
                    sheet_column_id("NOTIFICADO"): "={{ $json.NOTIFICADO }}",
                },
                "matchingColumns": ["row_number"],
                "schema": [
                    {
                        "id": "row_number",
                        "displayName": "row_number",
                        "required": False,
                        "defaultMatch": False,
                        "display": True,
                        "type": "number",
                        "canBeUsedToMatch": True,
                        "readOnly": True,
                    },
                    {
                        "id": sheet_column_id("NOTIFICADO"),
                        "displayName": sheet_display_name("NOTIFICADO"),
                        "required": False,
                        "defaultMatch": False,
                        "display": True,
                        "type": "string",
                        "canBeUsedToMatch": True,
                    },
                ],
                "attemptToConvertTypes": False,
                "convertFieldsToString": False,
            },
            "options": {},
        },
        "id": str(uuid.uuid4()),
        "name": NOTIFIER_MARK_NODE,
        "type": "n8n-nodes-base.googleSheets",
        "typeVersion": 4.5,
        "position": [base_pos[0] + 240, base_pos[1]],
        "retryOnFail": True,
        "maxTries": 5,
        "waitBetweenTries": 5000,
        "credentials": SHEETS_CREDENTIALS,
        "notes": (
            "Aggregate delivery: mark NOTIFICADO 🤖 on cdp_skus after final Telegram/email."
        ),
    }


def _load_shared_js(filename: str) -> str:
    return (SHARED_SRC / filename).read_text(encoding="utf-8")


def patch_notifier_rownum_lineage(wf: dict) -> bool:
    """Insert read + remap nodes so Google Sheets update keeps row_number pairedItem."""
    if wf.get("name") != "cdp_notifier":
        return False
    nodes = wf.setdefault("nodes", [])
    by_name = {node.get("name"): node for node in nodes}
    expand = by_name.get(NOTIFIER_EXPAND_NODE)
    mark = by_name.get(NOTIFIER_MARK_NODE)
    if not expand or not mark:
        return False

    changed = False
    expand_js = _load_shared_js("notifier_expandir_notificado.js")
    if expand.get("parameters", {}).get("jsCode") != expand_js:
        expand.setdefault("parameters", {})["jsCode"] = expand_js
        expand["notes"] = "Collapse row_numbers for NOTIFICADO; read+remap preserves sheet lineage."
        changed = True

    base_pos = expand.get("position", [2560, 360])
    mark_pos = mark.get("position", [base_pos[0] + 240, base_pos[1]])
    doc_id = mark.get("parameters", {}).get("documentId")
    sheet_name = mark.get("parameters", {}).get("sheetName")
    creds = mark.get("credentials")

    read = by_name.get(NOTIFIER_READ_NODE)
    if read is None:
        read = {
            "id": str(uuid.uuid4()),
            "name": NOTIFIER_READ_NODE,
            "type": "n8n-nodes-base.googleSheets",
            "typeVersion": 4.5,
            "position": [base_pos[0] + 80, base_pos[1]],
            "parameters": {
                "operation": "read",
                "documentId": doc_id,
                "sheetName": sheet_name,
                "options": {},
            },
            "notes": "Read SKUs rows so NOTIFICADO updates match by row_number.",
        }
        if creds:
            read["credentials"] = dict(creds)
        nodes.append(read)
        by_name[NOTIFIER_READ_NODE] = read
        changed = True

    remap = by_name.get(NOTIFIER_REMAP_NODE)
    remap_js = _load_shared_js("notifier_mapear_notificado.js")
    if remap is None:
        remap = {
            "id": str(uuid.uuid4()),
            "name": NOTIFIER_REMAP_NODE,
            "type": "n8n-nodes-base.code",
            "typeVersion": 2,
            "position": [base_pos[0] + 160, base_pos[1]],
            "parameters": {"jsCode": remap_js, "mode": "runOnceForAllItems"},
            "notes": "Merge NOTIFICADO onto sheet rows; preserve pairedItem for update.",
        }
        nodes.append(remap)
        by_name[NOTIFIER_REMAP_NODE] = remap
        changed = True
    elif remap.get("parameters", {}).get("jsCode") != remap_js:
        remap.setdefault("parameters", {})["jsCode"] = remap_js
        changed = True

    conns = wf.setdefault("connections", {})
    expand_conns = conns.get(NOTIFIER_EXPAND_NODE, {}).get("main", [[]])
    targets_read = any(
        link.get("node") == NOTIFIER_READ_NODE for branch in expand_conns for link in branch
    )
    if not targets_read:
        conns[NOTIFIER_EXPAND_NODE] = {
            "main": [[{"node": NOTIFIER_READ_NODE, "type": "main", "index": 0}]]
        }
        changed = True
    if NOTIFIER_READ_NODE not in conns:
        conns[NOTIFIER_READ_NODE] = {
            "main": [[{"node": NOTIFIER_REMAP_NODE, "type": "main", "index": 0}]]
        }
        changed = True
    else:
        read_targets_remap = any(
            link.get("node") == NOTIFIER_REMAP_NODE
            for branch in conns.get(NOTIFIER_READ_NODE, {}).get("main", [])
            for link in branch
        )
        if not read_targets_remap:
            conns[NOTIFIER_READ_NODE] = {
                "main": [[{"node": NOTIFIER_REMAP_NODE, "type": "main", "index": 0}]]
            }
            changed = True
    remap_targets_mark = any(
        link.get("node") == NOTIFIER_MARK_NODE
        for branch in conns.get(NOTIFIER_REMAP_NODE, {}).get("main", [])
        for link in branch
    )
    if NOTIFIER_REMAP_NODE not in conns or not remap_targets_mark:
        conns[NOTIFIER_REMAP_NODE] = {
            "main": [[{"node": NOTIFIER_MARK_NODE, "type": "main", "index": 0}]]
        }
        changed = True

    if mark_pos[0] < base_pos[0] + 200:
        mark["position"] = [base_pos[0] + 240, base_pos[1]]
        changed = True

    return changed


def ensure_notifier_sheet_update(wf: dict) -> bool:
    if wf.get("name") != "cdp_notifier":
        return False
    nodes = wf.setdefault("nodes", [])
    by_name = {node.get("name"): node for node in nodes}
    expand = by_name.get(NOTIFIER_EXPAND_NODE)
    if not expand:
        return False

    changed = False
    mark = by_name.get(NOTIFIER_MARK_NODE)
    if mark is None:
        nodes.append(notifier_mark_node(expand))
        changed = True
    else:
        changed = patch_sheet_name(mark) or changed

    conns = wf.setdefault("connections", {})
    expand_conns = conns.get(NOTIFIER_EXPAND_NODE, {}).get("main", [[]])
    already_linked = any(
        link.get("node") == NOTIFIER_MARK_NODE
        for branch in expand_conns
        for link in branch
    )
    if not already_linked:
        conns[NOTIFIER_EXPAND_NODE] = {
            "main": [[{"node": NOTIFIER_MARK_NODE, "type": "main", "index": 0}]]
        }
        changed = True
    return changed


def patch_workflow(path: Path) -> tuple[int, bool]:
    wf = json.loads(path.read_text(encoding="utf-8"))
    patched = 0
    for node in wf.get("nodes", []):
        if patch_sheet_name(node):
            patched += 1
    notifier_changed = ensure_notifier_sheet_update(wf)
    lineage_changed = patch_notifier_rownum_lineage(wf)
    if patched or notifier_changed or lineage_changed:
        path.write_text(json.dumps(wf, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return patched, notifier_changed or lineage_changed


def main() -> int:
    total = 0
    for path in WORKFLOWS:
        if not path.exists():
            print(f"skip missing {path.relative_to(ROOT)}")
            continue
        patched, notifier_changed = patch_workflow(path)
        total += patched
        extras = " + notifier NOTIFICADO node" if notifier_changed else ""
        print(f"Patched {path.relative_to(ROOT)} ({patched} sheet refs{extras})")
    print(f"Done ({total} sheet refs)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
