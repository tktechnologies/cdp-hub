#!/usr/bin/env python3
"""Inject n8n/src JS into cdp_router workflow Code nodes."""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SHARED = ROOT / "n8n" / "src"

NODE_FILES = {
    "🎲 Limitar SKUs": "router_limitar_skus.js",
    "🎲 Limitar SKUs (teste — remover depois)": "router_limitar_skus.js",
    "⚙️ Formatar Payload (Batches)": "formatar_payload_scraper.js",
    "⚙️ Formatar Payload Scraper": "formatar_payload_scraper.js",
    "📤 Router: Muvstok": "router_stokapi.js",
    "📤 Router: StokAPI": "router_stokapi.js",
    "📤 Router: API Diversos": "router_stokapi.js",
    "📋 Formatar erro Muvstok": "router_error_stokapi.js",
    "📋 Formatar erro StokAPI": "router_error_stokapi.js",
    "📋 Formatar erro API Diversos": "router_error_stokapi.js",
    "🔗 Emparelhar SKUs → PROCESSADO": "emparelhar_scraper.js",
    "📋 Formatar Confirmação (Planilha)": "router_confirmacao.js",
    "📱 Roteador de Comando": "router_telegram.js",
    "📊 Registrar Execução": "router_register_run.js",
    "📊 Status: preparar": "router_status_prepare.js",
    "📊 Formatar Status": "router_status.js",
    "📊 Progress: preparar runs": "progress_poll.js",
    "📊 Progress: formatar": "progress_format.js",
}

RENAME_NODES = {
    "🎲 Limitar SKUs (teste — remover depois)": "🎲 Limitar SKUs",
    "⚙️ Formatar Payload (Batches)": "⚙️ Formatar Payload Scraper",
    "📤 Router: Muvstok": "📤 Router: StokAPI",
    "🚀 POST Muvstok API": "🚀 POST StokAPI",
    "📦 Muvstok job aceito?": "📦 StokAPI job aceito?",
    "📋 Formatar erro Muvstok": "📋 Formatar erro StokAPI",
    "📱 Telegram: erro Muvstok": "📱 Telegram: erro StokAPI",
    "❓ Disparar Muvstok?": "❓ Disparar StokAPI?",
}

LEGACY_SAMPLE_MARKERS = (
    "const FIXED_DISPATCH_MAX_SKUS = 5",
    "const FIXED_MAX_SKUS = 5",
)


PROGRESS_WORKFLOW = ROOT / "n8n" / "workflows" / "cdp_progress.json"


def patch_workflow(path: pathlib.Path) -> None:
    wf = json.loads(path.read_text(encoding="utf-8"))
    workflow_name = path.stem
    name_map = dict(RENAME_NODES)

    for node in wf.get("nodes", []):
        old_name = node.get("name", "")
        if old_name in name_map:
            node["name"] = name_map[old_name]

    for node in wf.get("nodes", []):
        name = node.get("name", "")
        src = NODE_FILES.get(name)
        if not src:
            continue
        code = (SHARED / src).read_text(encoding="utf-8")
        if node.get("type", "").endswith("code"):
            node.setdefault("parameters", {})["jsCode"] = code
            node["parameters"]["mode"] = node["parameters"].get("mode", "runOnceForAllItems")

    stale: list[str] = []
    for node in wf.get("nodes", []):
        if not node.get("type", "").endswith("code"):
            continue
        code = node.get("parameters", {}).get("jsCode", "")
        if any(m in code for m in LEGACY_SAMPLE_MARKERS):
            stale.append(node.get("name", "?"))

    conns = wf.get("connections", {})
    new_conns = {}
    for key, val in conns.items():
        new_key = name_map.get(key, key)
        new_conns[new_key] = val
    for val in new_conns.values():
        for branch in val.get("main", []):
            for link in branch:
                if link.get("node") in name_map:
                    link["node"] = name_map[link["node"]]
    wf["connections"] = new_conns
    wf["name"] = workflow_name
    path.write_text(json.dumps(wf, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Patched {path} ({len(wf.get('nodes', []))} nodes)")
    if stale:
        print("ERROR: legacy 5-SKU cap still in nodes:", ", ".join(stale), file=sys.stderr)
        raise SystemExit(1)


def main() -> int:
    router = ROOT / "n8n" / "workflows" / "cdp_router.json"
    if not router.exists():
        print("cdp_router.json not found", file=sys.stderr)
        return 1
    patch_workflow(router)
    if PROGRESS_WORKFLOW.exists():
        patch_workflow(PROGRESS_WORKFLOW)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
