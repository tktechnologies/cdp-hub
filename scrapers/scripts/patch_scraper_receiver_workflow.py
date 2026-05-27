#!/usr/bin/env python3
"""Inject scraper Telegram formatter and harden NOTIFICADO / Telegram nodes."""
from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
WF_PATH = REPO_ROOT / "n8n/workflows/cdp_scraper.json"
TELEGRAM_FMT_PATH = REPO_ROOT / "n8n/lib/scraper_telegram_notification.js"

AD_HOC_GUARD = """
const q = wh.query || {};
const jmeta = typeof payload.job_metadata === 'object' && payload.job_metadata !== null ? payload.job_metadata : {};
if (String(jmeta.ad_hoc || q.ad_hoc || '').toLowerCase() === 'true') {
  return [];
}
"""

EXPANDIR_SIM_PREFIX = """function parseBody(raw) {
  let p = raw;
  if (typeof p === 'string') {
    try { p = JSON.parse(p); } catch (e) { p = {}; }
  }
  return p && typeof p === 'object' ? p : {};
}
const wh = $('🔔 Webhook: Receber Resultados').first().json;
const payload = parseBody(wh.body);
"""


def patch_expandir_notificado(code: str) -> str:
    if "ad_hoc" in code and "return []" in code:
        return code
    if EXPANDIR_SIM_PREFIX not in code:
        return code
    return code.replace(
        EXPANDIR_SIM_PREFIX,
        EXPANDIR_SIM_PREFIX + AD_HOC_GUARD,
        1,
    )


def patch_telegram_nodes(wf: dict) -> None:
    for node in wf["nodes"]:
        name = node.get("name", "")
        if "Telegram" not in name or node.get("type") != "n8n-nodes-base.telegram":
            continue
        node["retryOnFail"] = True
        node["maxTries"] = 3
        node["waitBetweenTries"] = 2000


def patch_notificado_sheets(wf: dict) -> None:
    for node in wf["nodes"]:
        if "Marcar NOTIFICADO" not in node.get("name", ""):
            continue
        if node.get("type") != "n8n-nodes-base.googleSheets":
            continue
        node["continueOnFail"] = True
        node["retryOnFail"] = True
        node["maxTries"] = 3
        node["waitBetweenTries"] = 2000


def main() -> None:
    wf = json.loads(WF_PATH.read_text(encoding="utf-8"))
    if TELEGRAM_FMT_PATH.is_file():
        tg_code = TELEGRAM_FMT_PATH.read_text(encoding="utf-8")
        for node in wf["nodes"]:
            if node.get("name") == "📣 Formatar Notificação Conclusão":
                node.setdefault("parameters", {})["jsCode"] = tg_code
                node["notes"] = "Assistente CDP — resumo sites + link relatório (lib)."
    for node in wf["nodes"]:
        name = node.get("name", "")
        if name in ("🔧 Expandir NOTIFICADO (✅ Sim)", "🔧 Expandir NOTIFICADO (❌ Não)", "🔧 Bulk: Expandir NOTIFICADO (✅ Sim)"):
            node["parameters"]["jsCode"] = patch_expandir_notificado(node["parameters"]["jsCode"])
    patch_telegram_nodes(wf)
    patch_notificado_sheets(wf)
    WF_PATH.write_text(json.dumps(wf, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Patched {WF_PATH}")


if __name__ == "__main__":
    main()
