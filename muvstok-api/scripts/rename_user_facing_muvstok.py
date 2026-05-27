#!/usr/bin/env python3
"""Replace user-facing 'muvstok' branding with 'api-diversos' / 'API Diversos'."""
from __future__ import annotations

import json
from pathlib import Path

SERVICE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[2]

# (old, new) — order matters for overlapping patterns
TEXT_REPLACEMENTS: list[tuple[str, str]] = [
    ("📦 *Muvstok job concluído*", "📦 *API Diversos job concluído*"),
    ("'SEM RESULTADOS MUVSTOK'", "'SEM RESULTADOS API-DIVERSOS'"),
    ("'MUVSTOK_OK'", "'API_DIVERSOS_OK'"),
    ("site_code: 'muvstok'", "site_code: 'api-diversos'"),
    ("site: filial || 'Muvstok'", "site: filial || 'API Diversos'"),
    ("site: 'Muvstok'", "site: 'API Diversos'"),
    (
        "// Shared helpers for n8n Muvstok receiver Code nodes",
        "// Shared helpers for n8n API Diversos receiver Code nodes",
    ),
    ("/** Muvstok Demand deep-link", "/** API Diversos Demand deep-link"),
    (
        "* Muvstok Demand API does not return",
        "* Demand API does not return",
    ),
    ("(found ? 'Muvstok' : 'N/A')", "(found ? 'API Diversos' : 'N/A')"),
    (
        "'Muvstok (API sem telefone/email/site por filial)'",
        "'API Diversos (API sem telefone/email/site por filial)'",
    ),
    ("🔔 Webhook Muvstok Result", "🔔 Webhook API Diversos Result"),
    ("📊 Extrair linhas Muvstok", "📊 Extrair linhas API Diversos"),
    ("📋 Extrair Resumo Muvstok", "📋 Extrair Resumo API Diversos"),
    ("📊 Construir Historico Muvstok", "📊 Construir Historico API Diversos"),
    ("Webhook_Muvstok_Result", "Webhook_Api_Diversos_Result"),
    ("Extrair_linhas_Muvstok", "Extrair_linhas_Api_Diversos"),
    ("Extrair_Resumo_Muvstok", "Extrair_Resumo_Api_Diversos"),
    ("Construir_Historico_Muvstok", "Construir_Historico_Api_Diversos"),
]

FILES = [
    REPO_ROOT / "n8n/lib/muvstok_sheet_helpers.js",
    SERVICE_ROOT / "scripts/patch_muvstok_receiver_workflow.py",
    REPO_ROOT / "n8n/workflows/cdp_stokapi.json",
    SERVICE_ROOT / "app/core/config.py",
    SERVICE_ROOT / "app/api/routes/health.py",
    SERVICE_ROOT / "app/services/auth_service.py",
    SERVICE_ROOT / "app/clients/muvstok_client.py",
    SERVICE_ROOT / "scripts/build_receiver_sdk.py",
]


def apply_replacements(text: str) -> str:
    for old, new in TEXT_REPLACEMENTS:
        text = text.replace(old, new)
    return text


def patch_workflow_json(path: Path) -> bool:
    data = json.loads(path.read_text(encoding="utf-8"))
    raw = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    updated = apply_replacements(raw)
    if updated == raw:
        return False
    path.write_text(updated, encoding="utf-8")
    return True


def main() -> None:
    changed: list[str] = []
    for path in FILES:
        if not path.exists():
            print(f"skip missing: {path}")
            continue
        if path.suffix == ".json" and "workflows" in path.parts:
            if patch_workflow_json(path):
                changed.append(str(path.relative_to(SERVICE_ROOT)))
            continue
        text = path.read_text(encoding="utf-8")
        updated = apply_replacements(text)
        if updated != text:
            path.write_text(updated, encoding="utf-8")
            changed.append(str(path.relative_to(SERVICE_ROOT)))
    print("Updated:", "\n  ".join(changed) if changed else "(none)")


if __name__ == "__main__":
    main()
