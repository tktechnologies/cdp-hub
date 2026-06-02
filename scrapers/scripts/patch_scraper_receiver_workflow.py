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

SHEET_STATUS_PRIORITY_JS = """function normalizeSheetStatus(value) {
  let s = String(value || '').trim().toLowerCase();
  try { s = s.normalize('NFD').replace(/[\\u0300-\\u036f]/g, ''); } catch (e) {}
  s = s.replace(/[^a-z0-9]+/g, ' ').trim();
  if (!s) return '';
  if (s.includes('sem preco') || s.includes('sem melhor preco') || s.includes('s preco') || s.includes('no price')) return 'sem_preco';
  if (s.includes('nao encontrado') || s.includes('not found')) return 'nao_encontrado';
  if (s.includes('bloqueado') || s.includes('blocked')) return 'bloqueado';
  if (s.includes('encontrado') || s === 'found') return 'encontrado';
  if (s.includes('processando') || s.includes('processing')) return 'processando';
  return s;
}
function sheetStatusRank(value) {
  const ranks = { processando: 0, nao_encontrado: 1, bloqueado: 2, sem_preco: 3, encontrado: 4 };
  const key = normalizeSheetStatus(value);
  return Object.prototype.hasOwnProperty.call(ranks, key) ? ranks[key] : -1;
}
function chooseSheetStatus(current, candidate) {
  return sheetStatusRank(current) > sheetStatusRank(candidate) ? current : candidate;
}
"""

SCRAPER_RESUMO_JS = """// v0.8.6: summary rows + sticky sheet status vocabulary
function parseBody(raw) {
  let p = raw;
  if (typeof p === 'string') {
    try { p = JSON.parse(p); } catch (e) { p = {}; }
  }
  return p && typeof p === 'object' ? p : {};
}

const STATUS = {
  FOUND: '✅ Encontrado',
  NOT_FOUND: '❌ Não encontrado',
  NO_PRICE: '⚠️ Sem preço',
  BLOCKED: '🚫 Bloqueado',
};

function siteStatuses(skuResult) {
  return (Array.isArray(skuResult.site_results) ? skuResult.site_results : [])
    .map((sr) => String(sr.status || '').trim().toLowerCase())
    .filter(Boolean);
}

function sheetStatusForSku(skuResult, hasResults, bestPrice) {
  const statuses = siteStatuses(skuResult);
  if (bestPrice) return STATUS.FOUND;
  if (hasResults || statuses.includes('no_price')) return STATUS.NO_PRICE;
  if (statuses.includes('blocked')) return STATUS.BLOCKED;
  return STATUS.NOT_FOUND;
}

const wh = $('🔔 Webhook: Receber Resultados').first().json;
const payload = parseBody(wh.body);

const skipEncontrado = false;
const results = Array.isArray(payload.results) ? payload.results : [];
const rows = [];

for (const skuResult of results) {
  const sku = skuResult.sku || '';
  const hasResults = (skuResult.total_results || 0) > 0;

  let bestPrice = null;
  let bestSite = '';
  let bestUrl = '';
  for (const sr of skuResult.site_results || []) {
    for (const part of sr.results || []) {
      if (part.price != null && part.price > 0) {
        if (!bestPrice || part.price < bestPrice) {
          bestPrice = part.price;
          bestSite = sr.site_name || sr.site || '';
          bestUrl = part.product_url || '';
        }
      }
    }
  }

  if (!bestSite && hasResults) {
    for (const sr of skuResult.site_results || []) {
      for (const part of sr.results || []) {
        const u = String(part.product_url || '').trim();
        if (u) {
          bestSite = sr.site_name || sr.site || '';
          bestUrl = u;
          break;
        }
      }
      if (bestSite) break;
    }
  }

  const status = sheetStatusForSku(skuResult, hasResults, bestPrice);

  let melhor = 'N/A';
  if (bestPrice) {
    melhor = 'R$ ' + bestPrice.toLocaleString('pt-BR', { minimumFractionDigits: 2 });
  } else if (hasResults) {
    melhor = 'S/ preço (ver Detalhado)';
  }

  rows.push({
    CODIGO: sku,
    STATUS: status,
    MELHOR_PRECO: melhor,
    SITE: bestSite || 'N/A',
    LINK: bestUrl || 'N/A',
    DATA: new Date().toLocaleDateString('pt-BR'),
    _encontrado: status,
  });
}

return rows.map((r) => ({ json: { ...r, _skip_encontrado: skipEncontrado } }));
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


# --- row_number duplicate-marking pipeline ----------------------------------
# All CDP_SKUs writebacks matched on CODIGO, so only the FIRST row sharing a SKU
# was ever marked — duplicate CODIGO rows stayed blank. We splice
# collapse → read → remap before each marker so each duplicate row is updated by
# its own row_number. The collapse node makes the sheet read run exactly once and
# also merges the two NOTIFICADO feeders (✅ Sim / ❌ Não) into a single payload.
def _clone(obj):
    return json.loads(json.dumps(obj))


def _schema_entry(col_id, col_type, *, match=False, read_only=False):
    entry = {
        "id": col_id,
        "displayName": col_id,
        "required": False,
        "defaultMatch": False,
        "display": True,
        "type": col_type,
        "canBeUsedToMatch": True,
    }
    if read_only:
        entry["readOnly"] = True
    return entry


def _splice_rownum_marker(wf, *, update_name, producers, names, ids, remap_value_js, update_value, schema):
    """Insert collapse → read → remap between `producers` and the update node."""
    nodes = wf["nodes"]
    by_name = {n["name"]: n for n in nodes}
    if update_name not in by_name:
        return
    upd = by_name[update_name]
    base = upd.get("position", [0, 0])
    collapse_name, read_name, remap_name = names

    collapse_node = {
        "id": ids[0],
        "name": collapse_name,
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [base[0] - 660, base[1]],
        "parameters": {"jsCode": "const marks = $input.all().map((i) => i.json);\nreturn [{ json: { marks } }];\n"},
        "notes": "Collapse marking items into one payload so the sheet read runs once (and merge feeders).",
    }
    read_node = {
        "id": ids[1],
        "name": read_name,
        "type": "n8n-nodes-base.googleSheets",
        "typeVersion": 4.5,
        "position": [base[0] - 440, base[1]],
        "parameters": {
            "operation": "read",
            "documentId": _clone(upd["parameters"]["documentId"]),
            "sheetName": _clone(upd["parameters"]["sheetName"]),
            "options": {},
        },
        "notes": "Read SKUs rows (CODIGO + row_number) so every duplicate CODIGO row can be marked.",
    }
    if upd.get("credentials"):
        read_node["credentials"] = _clone(upd["credentials"])
    remap_js = (
        "const marks = $('" + collapse_name + "').first().json.marks || [];\n"
        "const byCodigo = {};\n"
        "for (const it of marks) {\n"
        "  const k = String(it.CODIGO == null ? '' : it.CODIGO).trim().toUpperCase();\n"
        "  if (k) byCodigo[k] = it;\n"
        "}\n"
        + SHEET_STATUS_PRIORITY_JS
        + "const rows = $input.all().map((i) => i.json);\n"
        "const out = [];\n"
        "for (const row of rows) {\n"
        "  const rn = row.row_number;\n"
        "  if (rn === undefined || rn === null || rn === '') continue;\n"
        "  const k = String(row.CODIGO == null ? '' : row.CODIGO).trim().toUpperCase();\n"
        "  const it = byCodigo[k];\n"
        "  if (!it) continue;\n"
        "  out.push({ json: " + remap_value_js + " });\n"
        "}\n"
        "return out;\n"
    )
    remap_node = {
        "id": ids[2],
        "name": remap_name,
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [base[0] - 220, base[1]],
        "parameters": {"jsCode": remap_js},
        "notes": "Fan out one update per matching sheet row_number (handles duplicate CODIGO rows).",
    }

    for new_node in (collapse_node, read_node, remap_node):
        if new_node["name"] in by_name:
            nodes[nodes.index(by_name[new_node["name"]])] = new_node
        else:
            nodes.append(new_node)

    conns = wf["connections"]
    for producer in producers:
        for outset in conns.get(producer, {}).get("main", []) or []:
            for conn in outset or []:
                if conn.get("node") == update_name:
                    conn["node"] = collapse_name
    conns[collapse_name] = {"main": [[{"node": read_name, "type": "main", "index": 0}]]}
    conns[read_name] = {"main": [[{"node": remap_name, "type": "main", "index": 0}]]}
    conns[remap_name] = {"main": [[{"node": update_name, "type": "main", "index": 0}]]}

    cols = upd["parameters"]["columns"]
    cols["mappingMode"] = "defineBelow"
    cols["value"] = update_value
    cols["matchingColumns"] = ["row_number"]
    cols["schema"] = schema


def patch_rownum_markers(wf: dict) -> None:
    _splice_rownum_marker(
        wf,
        update_name="✅ Marcar ENCONTRADO → CDP_SKUs",
        producers=["❓ Atualizar ENCONTRADO na planilha?"],
        names=("🧺 Coletar ENCONTRADO", "📄 Ler CDP_SKUs (ENCONTRADO)", "🧭 Mapear ENCONTRADO por row"),
        ids=(
            "ea9759a1-e612-4aa2-9cbb-68e8406dee26",
            "99e08055-40e6-4304-8cd9-48b48ede9872",
            "29bd78b2-edc9-428c-bcef-3088ab6b7f69",
        ),
        remap_value_js="{ row_number: rn, PROCESSADO: '✅ Processado', ENCONTRADO: chooseSheetStatus(row.ENCONTRADO, it._encontrado) }",
        update_value={
            "row_number": "={{ $json.row_number }}",
            "PROCESSADO": "={{ $json.PROCESSADO }}",
            "ENCONTRADO": "={{ $json.ENCONTRADO }}",
        },
        schema=[
            _schema_entry("row_number", "number", match=True, read_only=True),
            _schema_entry("PROCESSADO", "string"),
            _schema_entry("ENCONTRADO", "string"),
        ],
    )
    _splice_rownum_marker(
        wf,
        update_name="✅ Marcar NOTIFICADO → CDP_SKUs",
        producers=["🔧 Expandir NOTIFICADO (✅ Sim)", "🔧 Expandir NOTIFICADO (❌ Não)"],
        names=("🧺 Coletar NOTIFICADO", "📄 Ler CDP_SKUs (NOTIFICADO)", "🧭 Mapear NOTIFICADO por row"),
        ids=(
            "c899ab4a-73d4-49b0-8c34-9dd2a0ae43c5",
            "534799f9-6f03-4d36-b787-bfda68cd9e08",
            "dd367c1d-91b8-4b7b-afe6-17501dae61d8",
        ),
        remap_value_js="{ row_number: rn, NOTIFICADO: it.NOTIFICADO }",
        update_value={
            "row_number": "={{ $json.row_number }}",
            "NOTIFICADO": "={{ $json.NOTIFICADO }}",
        },
        schema=[
            _schema_entry("row_number", "number", match=True, read_only=True),
            _schema_entry("NOTIFICADO", "string"),
        ],
    )
    _splice_rownum_marker(
        wf,
        update_name="✅ Bulk: Marcar NOTIFICADO → CDP_SKUs",
        producers=["🔧 Bulk: Expandir NOTIFICADO (✅ Sim)"],
        names=("🧺 Bulk: Coletar NOTIFICADO", "📄 Bulk: Ler CDP_SKUs (NOTIFICADO)", "🧭 Bulk: Mapear NOTIFICADO por row"),
        ids=(
            "f858a6df-4895-4206-a5d4-40ff33b869b5",
            "14ab52e5-660f-4b8f-9649-d55b9b3a4a74",
            "6384dbec-f061-4d96-bafa-5c0c97f9e669",
        ),
        remap_value_js="{ row_number: rn, NOTIFICADO: it.NOTIFICADO }",
        update_value={
            "row_number": "={{ $json.row_number }}",
            "NOTIFICADO": "={{ $json.NOTIFICADO }}",
        },
        schema=[
            _schema_entry("row_number", "number", match=True, read_only=True),
            _schema_entry("NOTIFICADO", "string"),
        ],
    )


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
        if name == "📋 Extrair Resumo":
            node["parameters"]["jsCode"] = SCRAPER_RESUMO_JS
        elif name == "✅ Marcar ENCONTRADO → CDP_SKUs":
            node["notes"] = (
                "Updates PROCESSADO/ENCONTRADO by row_number using sticky status priority "
                "(Encontrado/Sem preço are not downgraded by later Não encontrado callbacks)."
            )
        elif name == "✅ Bulk: Marcar NOTIFICADO → CDP_SKUs":
            node["notes"] = (
                "Updates NOTIFICADO=✅ Sim for all SKUs in this job by row_number. | "
                "v0.8.0: retry 5x/5s; no continueOnFail (retries work; fail loud if Sheets still errors)."
            )
        if name in ("🔧 Expandir NOTIFICADO (✅ Sim)", "🔧 Expandir NOTIFICADO (❌ Não)", "🔧 Bulk: Expandir NOTIFICADO (✅ Sim)"):
            node["parameters"]["jsCode"] = patch_expandir_notificado(node["parameters"]["jsCode"])
            if name == "🔧 Bulk: Expandir NOTIFICADO (✅ Sim)":
                node["parameters"]["jsCode"] = node["parameters"]["jsCode"].replace("✅ Sim (Bulk)", "✅ Sim")
    patch_telegram_nodes(wf)
    patch_notificado_sheets(wf)
    patch_rownum_markers(wf)
    WF_PATH.write_text(json.dumps(wf, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Patched {WF_PATH}")


if __name__ == "__main__":
    main()
