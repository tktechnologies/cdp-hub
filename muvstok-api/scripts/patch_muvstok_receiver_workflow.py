#!/usr/bin/env python3
"""Inject shared Muvstok sheet helpers and fix receiver Code nodes + cdp_skus match."""
from __future__ import annotations

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
WF_PATH = REPO_ROOT / "n8n/workflows/cdp_stokapi.json"
HELPERS_PATH = REPO_ROOT / "n8n/lib/muvstok_sheet_helpers.js"
TELEGRAM_FMT_PATH = REPO_ROOT / "n8n/lib/muvstok_telegram_formatter.js"

MARKER_START = "// --- muvstok_sheet_helpers (auto) ---"
MARKER_END = "// --- end muvstok_sheet_helpers ---"

LISTING_ROW_FN = r"""function listingRow(sku, row, statusItem, searchTimeMs) {
  const skuSearched = na(sku).toUpperCase();
  const skuFound = na(pickField(row, 'sku', 'SKU', 'skuSemCaractereEspecial') || sku);
  const stock = pickField(row, 'qtdeEstoque', 'qtdEstoque', 'stock_quantity');
  const filial = branchLabel(row);
  const saleStr = naSalePriceFromRow(row);
  const costStr = naCostPriceFromRow(row);
  const tipoCode = stockTypeCode(row);
  const ms = Number(searchTimeMs);
  const encontrado = saleStr ? '✅ Encontrado' : '⚠️ Sem preço';
  return {
    job_id: jobId,
    sku_searched: skuSearched,
    sku_found: skuFound || 'N/A',
    exact_match: toBoolPt(skuFound && skuSearched === String(skuFound).trim().toUpperCase()),
    site: CDP_SITE_LABEL,
    price: saleStr,
    preco_medio: costStr,
    currency: 'BRL',
    availability: toAvailabilityPt(stock),
    seller: filial || 'N/A',
    product_url: productUrlForSheet(skuSearched, row),
    origin: 'Brasil',
    raw_title: productTitle(row) || na(statusItem),
    scraped_at: completedAt,
    search_time_ms: String(Number.isFinite(ms) && ms >= 0 ? Math.round(ms) : 0),
    condition: 'novo',
    job_duration_s: String(jobDuration),
    brand: brandLabel(row) || 'N/A',
    site_code: CDP_SITE_CODE,
    melibox_posicao: 'N/A',
    melibox_tipo: tipoCode !== '' ? tipoCode : 'N/A',
    melibox_oferta_pct: 'N/A',
    melibox_envio: 'N/A',
    melibox_frete: 'N/A',
    melibox_pagina: 'N/A',
    _encontrado: encontrado,
  };
}"""

MARK_SKU_FN = r"""function markSku(sku, status) {
  function normalizeSheetStatus(value) {
    let s = String(value || '').trim().toLowerCase();
    try { s = s.normalize('NFD').replace(/[\u0300-\u036f]/g, ''); } catch (e) {}
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

  const key = String(sku || '').trim().toUpperCase();
  if (!key) return;
  const next = String(status || '').trim() || '❌ Não encontrado';
  if (!skuSummaries[key]) {
    skuSummaries[key] = { sku: key, listing_count: 0, found: false, encontrado: '❌ Não encontrado' };
  }
  const chosen = chooseSheetStatus(skuSummaries[key].encontrado, next);
  skuSummaries[key].encontrado = chosen;
  const normalized = normalizeSheetStatus(chosen);
  skuSummaries[key].found = normalized === 'encontrado' || normalized === 'sem_preco';
  skuSummaries[key].listing_count += 1;
  if (!skuList.includes(key)) skuList.push(key);
}"""

DETALHADO_PATCHES: list[tuple[str, str]] = [
    ("origem: 'muvstok',", "origem: CDP_ORIGEM_LABEL,"),
    (
        "resumo_sites: JSON.stringify({ muvstok: skuHitPct }),",
        "resumo_sites: JSON.stringify({ [CDP_SITE_CODE]: skuHitPct }),",
    ),
    ("'SEM RESULTADOS API-DIVERSOS'", "'SEM RESULTADOS API DIVERSOS'"),
    ("'SEM RESULTADOS MUVSTOK'", "'SEM RESULTADOS API DIVERSOS'"),
    ("site: 'muvstok',", "site: CDP_SITE_LABEL,"),
    ("site_code: 'muvstok',", "site_code: CDP_SITE_CODE,"),
    ("site_code: 'api-diversos',", "site_code: CDP_SITE_CODE,"),
    (
        "const jobDuration = Number(payload.duration_seconds || 0);",
        "const jobDuration = resolveJobDurationSeconds(payload, meta, completedAt, startedAt);",
    ),
    (
        "pushDetalhado(listingRow(sku, row, 'succeeded'));",
        "pushDetalhado(listingRow(sku, row, 'succeeded', skuSearchTimeMs(skuResult)));",
    ),
    (
        "product_url: buildDemandUrl(sku),\n        origin: 'N/A',\n        raw_title: na(skuResult.status || 'not_found').toUpperCase(),\n        scraped_at: completedAt,\n        search_time_ms: String(skuSearchTimeMs(skuResult)),",
        "product_url: productUrlForSheet(sku, null),\n        origin: 'N/A',\n        raw_title: na(skuResult.status || 'not_found').toUpperCase(),\n        scraped_at: completedAt,\n        search_time_ms: String(skuSearchTimeMs(skuResult)),",
    ),
    (
        "product_url: buildContactInfo(sku, null),\n        origin: 'N/A',\n        raw_title: na(skuResult.status || 'not_found').toUpperCase(),\n        scraped_at: completedAt,\n        search_time_ms: String(skuSearchTimeMs(skuResult)),",
        "product_url: productUrlForSheet(sku, null),\n        origin: 'N/A',\n        raw_title: na(skuResult.status || 'not_found').toUpperCase(),\n        scraped_at: completedAt,\n        search_time_ms: String(skuSearchTimeMs(skuResult)),",
    ),
    (
        "site: 'API Diversos',\n        price: 'N/A',\n        currency: 'BRL',\n        availability: 'nao_encontrado',\n        seller: 'N/A',\n        product_url: buildDemandUrl(sku),",
        "site: CDP_SITE_LABEL,\n        price: 'N/A',\n        currency: 'BRL',\n        availability: 'nao_encontrado',\n        seller: 'N/A',\n        product_url: productUrlForSheet(sku, null),",
    ),
    (
        "product_url: buildContactInfo(skuSearched, row),",
        "product_url: productUrlForSheet(skuSearched, row),",
    ),
    (
        "product_url: buildProductUrl(skuSearched, row),",
        "product_url: productUrlForSheet(skuSearched, row),",
    ),
    (
        "product_url: 'N/A',",
        "product_url: '',",
    ),
    (
        "brand: na(pickField(row, 'montadora', 'automaker')),",
        "brand: brandLabel(row) || 'N/A',",
    ),
    (
        "price: 'N/A',\n        currency: 'BRL',",
        "price: 'N/A',\n        preco_medio: 'N/A',\n        currency: 'BRL',",
    ),
    ("LINK: 'N/A'", "LINK: ''"),
    (
        "product_url: buildDemandUrl(sku),",
        "product_url: productUrlForSheet(sku),",
    ),
]

RESUMO_PATCHES: list[tuple[str, str]] = [
    ("LINK: 'N/A',", "LINK: '',"),
    (
        "LINK: link,",
        "LINK: '',",
    ),
]

RESUMO_PUSH_FN = r"""function pushResumo(out, sku, listings, st, skuResult) {
  const skuStr = String(sku || '').trim();
  if (!skuStr) return;
  const offer = bestOfferFromListings(listings);
  const bestPrice = offer.bestPrice;
  const bestSite = offer.bestSite;
  const statusLower = String(st || '').toLowerCase();
  const apiOk = statusLower === 'succeeded' || statusLower === 'success';
  const hasListings = rowsForPricing(listings).length > 0;
  const found = hasListings || apiOk;
  let status = '❌ Não encontrado';
  if (found && bestPrice !== null) status = '✅ Encontrado';
  else if (found) status = '⚠️ Sem preço';
  const melhor = formatResumoPreco(bestPrice);
  out.push({
    json: {
      CODIGO: skuStr,
      STATUS: status,
      MELHOR_PRECO: melhor,
      SITE: bestSite || (found ? CDP_SITE_LABEL : 'N/A'),
      LINK: '',
      DATA: new Date().toLocaleDateString('pt-BR'),
    },
  });
}"""

# --- row_number duplicate-marking pipeline (handles duplicate CODIGO rows) ---
# StokAPI dedups SKUs at ingestion, so a single result must mark EVERY sheet row
# sharing that CODIGO. We read the sheet, fan out one update per matching row_number,
# and match on row_number (not CODIGO) so duplicates are no longer skipped.
LER_LINHAS_NAME = "📄 Ler CDP_SKUs (linhas)"
LER_LINHAS_ID = "d83f487f-38f5-4d1c-bac9-ca91f82598c8"
MAPEAR_NAME = "🧭 Mapear linhas por CODIGO"
MAPEAR_ID = "2576a2a9-eed8-4b69-a4aa-bc81e629aeb4"
HISTORICO_NAME = "📊 Construir Historico API Diversos"
ATUALIZAR_NAME = "✅ Atualizar CDP_SKUs"
SKUS_PARA_ATUALIZAR_NAME = "📋 SKUs para atualizar"

LER_LINHAS_NOTES = (
    "Reads SKUs rows (CODIGO + row_number) so duplicate CODIGO rows can each be marked "
    "by row_number. Single input item (from Historico) → runs once."
)
MAPEAR_NOTES = (
    "Fan out one update per sheet row by row_number. Code node runs once over all rows; "
    "reads sku_updates from staticData (set by Extrair linhas)."
)
SHEET_STATUS_PRIORITY_JS = (
    "function normalizeSheetStatus(value) {\n"
    "  let s = String(value || '').trim().toLowerCase();\n"
    "  try { s = s.normalize('NFD').replace(/[\\u0300-\\u036f]/g, ''); } catch (e) {}\n"
    "  s = s.replace(/[^a-z0-9]+/g, ' ').trim();\n"
    "  if (!s) return '';\n"
    "  if (s.includes('sem preco') || s.includes('sem melhor preco') || s.includes('s preco') || s.includes('no price')) return 'sem_preco';\n"
    "  if (s.includes('nao encontrado') || s.includes('not found')) return 'nao_encontrado';\n"
    "  if (s.includes('bloqueado') || s.includes('blocked')) return 'bloqueado';\n"
    "  if (s.includes('encontrado') || s === 'found') return 'encontrado';\n"
    "  if (s.includes('processando') || s.includes('processing')) return 'processando';\n"
    "  return s;\n"
    "}\n"
    "function sheetStatusRank(value) {\n"
    "  const ranks = { processando: 0, nao_encontrado: 1, bloqueado: 2, sem_preco: 3, encontrado: 4 };\n"
    "  const key = normalizeSheetStatus(value);\n"
    "  return Object.prototype.hasOwnProperty.call(ranks, key) ? ranks[key] : -1;\n"
    "}\n"
    "function chooseSheetStatus(current, candidate) {\n"
    "  return sheetStatusRank(current) > sheetStatusRank(candidate) ? current : candidate;\n"
    "}\n"
)
MAPEAR_JS = (
    "// Map each API Diversos result SKU to ALL matching sheet rows (handles duplicate CODIGO rows).\n"
    "let meta = {};\n"
    "try {\n"
    "  if (typeof $getWorkflowStaticData === 'function') {\n"
    "    meta = $getWorkflowStaticData('global').muvstok_last_callback || {};\n"
    "  }\n"
    "} catch (e) {}\n"
    "const updates = Array.isArray(meta.sku_updates) ? meta.sku_updates : [];\n"
    "const byCodigo = {};\n"
    "for (const u of updates) {\n"
    "  const key = String(u.sku == null ? '' : u.sku).trim().toUpperCase();\n"
    "  if (key) byCodigo[key] = u;\n"
    "}\n"
    + SHEET_STATUS_PRIORITY_JS
    + "const rows = $input.all().map((i) => i.json);\n"
    "const out = [];\n"
    "for (const row of rows) {\n"
    "  const rn = row.row_number;\n"
    "  if (rn === undefined || rn === null || rn === '') continue;\n"
    "  const codigo = String(row.CODIGO == null ? '' : row.CODIGO).trim().toUpperCase();\n"
    "  const u = byCodigo[codigo];\n"
    "  if (!u) continue;\n"
    "  const encontrado = chooseSheetStatus(row.ENCONTRADO, u.ENCONTRADO);\n"
    "  out.push({ json: { row_number: rn, PROCESSADO: u.PROCESSADO, ENCONTRADO: encontrado } });\n"
    "}\n"
    "return out;\n"
)


def _clone(obj):
    return json.loads(json.dumps(obj))


def patch_rownum_pipeline(wf: dict) -> None:
    """Insert read → remap nodes between Historico and ✅ Atualizar CDP_SKUs (idempotent)."""
    nodes = wf["nodes"]
    by_name = {n["name"]: n for n in nodes}
    update_node = by_name[ATUALIZAR_NAME]

    read_node = {
        "id": LER_LINHAS_ID,
        "name": LER_LINHAS_NAME,
        "type": "n8n-nodes-base.googleSheets",
        "typeVersion": 4.5,
        "position": [400, 160],
        "parameters": {
            "operation": "read",
            "documentId": _clone(update_node["parameters"]["documentId"]),
            "sheetName": _clone(update_node["parameters"]["sheetName"]),
            "options": {},
        },
        "notes": LER_LINHAS_NOTES,
    }
    if update_node.get("credentials"):
        read_node["credentials"] = _clone(update_node["credentials"])

    map_node = {
        "id": MAPEAR_ID,
        "name": MAPEAR_NAME,
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [620, 160],
        "parameters": {"jsCode": MAPEAR_JS},
        "notes": MAPEAR_NOTES,
    }

    for new_node in (read_node, map_node):
        if new_node["name"] in by_name:
            nodes[nodes.index(by_name[new_node["name"]])] = new_node
        else:
            nodes.append(new_node)

    conns = wf["connections"]

    # 📋 SKUs para atualizar no longer feeds the update node (Telegram only).
    sp = conns.get(SKUS_PARA_ATUALIZAR_NAME, {}).get("main")
    if sp and sp[0]:
        sp[0][:] = [c for c in sp[0] if c.get("node") != ATUALIZAR_NAME]

    # 📊 Construir Historico → 📄 Ler CDP_SKUs (linhas) (keep existing Historico-save edge).
    hist_main = conns.setdefault(HISTORICO_NAME, {"main": [[]]})["main"]
    if not hist_main:
        hist_main.append([])
    if LER_LINHAS_NAME not in {c.get("node") for c in hist_main[0]}:
        hist_main[0].append({"node": LER_LINHAS_NAME, "type": "main", "index": 0})

    conns[LER_LINHAS_NAME] = {"main": [[{"node": MAPEAR_NAME, "type": "main", "index": 0}]]}
    conns[MAPEAR_NAME] = {"main": [[{"node": ATUALIZAR_NAME, "type": "main", "index": 0}]]}


# Inline duplicates injected before patch cleanup — shadow pickField-based helpers.
SHADOWED_FUNCTION_NAMES = (
    "stockQty",
    "isEmEstoque",
    "filterInStock",
    "parsePrice",
    "readEnv",
    "naPrice",
)


def inject_helpers(code: str, helpers: str) -> str:
    block = f"{MARKER_START}\n{helpers.strip()}\n{MARKER_END}\n\n"
    if MARKER_START in code:
        pattern = rf"{re.escape(MARKER_START)}.*?{re.escape(MARKER_END)}\n\n"
        code = re.sub(pattern, lambda _m: block, code, count=1, flags=re.DOTALL)
    else:
        code = block + code
    return code


def strip_shadowed_helpers(code: str) -> str:
    """Remove duplicate function declarations in the node preamble (after helpers, before main)."""
    if MARKER_END not in code:
        return code
    head, tail = code.split(MARKER_END, 1)
    tail = tail.lstrip("\n")
    # Only strip shadow copies before main logic — never touch the injected helper block in `head`.
    split_at = re.search(r"\n(const wh = \$input\.first\(\)|function parseBody\()", tail)
    if not split_at:
        return head + MARKER_END + "\n\n" + tail
    preamble, main = tail[: split_at.start()], tail[split_at.start() :]
    for name in SHADOWED_FUNCTION_NAMES:
        pattern = rf"function {re.escape(name)}\([^)]*\) \{{[\s\S]*?\n\}}\n"
        preamble = re.sub(pattern, "", preamble, count=1)
    return head + MARKER_END + "\n\n" + preamble.lstrip("\n") + main


def replace_function(code: str, name: str, new_body: str) -> str:
    pattern = rf"function {re.escape(name)}\([^)]*\) \{{"
    m = re.search(pattern, code)
    if not m:
        raise RuntimeError(f"function {name} not found")
    start = m.start()
    depth = 0
    i = m.end() - 1
    while i < len(code):
        if code[i] == "{":
            depth += 1
        elif code[i] == "}":
            depth -= 1
            if depth == 0:
                return code[:start] + new_body.strip() + code[i + 1 :]
        i += 1
    raise RuntimeError(f"unbalanced braces in {name}")


def patch_detalhado(code: str, helpers: str) -> str:
    code = inject_helpers(code, helpers)
    code = strip_shadowed_helpers(code)
    code = replace_function(code, "listingRow", LISTING_ROW_FN)
    code = replace_function(code, "markSku", MARK_SKU_FN)
    code = code.replace("markSku(sku, false);", "markSku(sku, '❌ Não encontrado');")
    code = code.replace(
        "markSku(sku, true);\n      pushDetalhado(listingRow(sku, row, 'succeeded', skuSearchTimeMs(skuResult)));",
        "const detail = listingRow(sku, row, 'succeeded', skuSearchTimeMs(skuResult));\n      markSku(sku, detail._encontrado);\n      pushDetalhado(detail);",
    )
    code = code.replace(
        "markSku(sku, found);",
        "markSku(sku, found ? '✅ Encontrado' : '❌ Não encontrado');",
    )
    code = code.replace("'✗ Não encontrado'", "'❌ Não encontrado'")
    code = code.replace("PROCESSADO: 'processado'", "PROCESSADO: '✅ Processado'")
    code = code.replace(
        "ENCONTRADO: s.found ? '✅ Encontrado' : '❌ Não encontrado'",
        "ENCONTRADO: s.encontrado || (s.found ? '✅ Encontrado' : '❌ Não encontrado')",
    )
    for old, new in DETALHADO_PATCHES:
        if new in code:
            continue
        if old not in code:
            continue
        code = code.replace(old, new, 1)
    return code


def patch_resumo(code: str, helpers: str) -> str:
    code = inject_helpers(code, helpers)
    code = strip_shadowed_helpers(code)
    code = replace_function(code, "pushResumo", RESUMO_PUSH_FN)
    code = code.replace(
        "pushResumo(out, sr.sku, listings, sr.status);",
        "pushResumo(out, sr.sku, listings, sr.status, sr);",
    )
    code = code.replace(
        "pushResumo(out, item.sku, [], item.status);",
        "pushResumo(out, item.sku, [], item.status, item);",
    )
    for old, new in RESUMO_PATCHES:
        if new in code:
            continue
        if old not in code:
            continue
        code = code.replace(old, new, 1)
    return code


def patch_detalhado_sheet_columns(wf: dict) -> None:
    node = next(n for n in wf["nodes"] if n["name"] == "📊 Salvar → CDP_Resultados (Detalhado)")
    cols = node["parameters"]["columns"]
    value = dict(cols.get("value") or {})
    if "preco-medio" not in value:
        ordered: dict[str, str] = {}
        for key, expr in value.items():
            ordered[key] = expr
            if key == "preco":
                ordered["preco-medio"] = "={{ $json.preco_medio }}"
        if "preco-medio" not in ordered:
            ordered["preco-medio"] = "={{ $json.preco_medio }}"
        cols["value"] = ordered


def patch_cdp_skus_node(wf: dict) -> None:
    """Match on row_number (not CODIGO) so every duplicate CODIGO row is marked.

    The upstream 🧭 Mapear linhas por CODIGO node fans out one item per matching
    sheet row, each carrying its own row_number. Matching on CODIGO would only ever
    touch the first row sharing a SKU, leaving duplicate rows blank.
    """
    node = next(n for n in wf["nodes"] if n["name"] == "✅ Atualizar CDP_SKUs")
    cols = node["parameters"]["columns"]
    cols["mappingMode"] = "defineBelow"
    cols["value"] = {
        "row_number": "={{ $json.row_number }}",
        "PROCESSADO": "={{ $json.PROCESSADO }}",
        "ENCONTRADO": "={{ $json.ENCONTRADO }}",
    }
    cols["matchingColumns"] = ["row_number"]
    cols["schema"] = [
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
            "id": "PROCESSADO",
            "displayName": "PROCESSADO",
            "required": False,
            "defaultMatch": False,
            "display": True,
            "type": "string",
            "canBeUsedToMatch": True,
        },
        {
            "id": "ENCONTRADO",
            "displayName": "ENCONTRADO",
            "required": False,
            "defaultMatch": False,
            "display": True,
            "type": "string",
            "canBeUsedToMatch": True,
        },
    ]


def main() -> None:
    helpers = HELPERS_PATH.read_text(encoding="utf-8")
    wf = json.loads(WF_PATH.read_text(encoding="utf-8"))
    for node in wf["nodes"]:
        if node["name"] == "📊 Extrair linhas API Diversos":
            node["parameters"]["jsCode"] = patch_detalhado(node["parameters"]["jsCode"], helpers)
        elif node["name"] == "📋 Extrair Resumo API Diversos":
            node["parameters"]["jsCode"] = patch_resumo(node["parameters"]["jsCode"], helpers)
    patch_rownum_pipeline(wf)
    patch_cdp_skus_node(wf)
    patch_detalhado_sheet_columns(wf)
    if TELEGRAM_FMT_PATH.is_file():
        tg_code = TELEGRAM_FMT_PATH.read_text(encoding="utf-8")
        for node in wf["nodes"]:
            if node.get("name") == "📣 Formatar Telegram":
                node.setdefault("parameters", {})["jsCode"] = tg_code
            if node.get("name") == "📱 Telegram":
                af = node.setdefault("parameters", {}).setdefault("additionalFields", {})
                af["appendAttribution"] = False
                node["retryOnFail"] = True
                node["maxTries"] = 3
                node["waitBetweenTries"] = 2000
    WF_PATH.write_text(json.dumps(wf, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Patched {WF_PATH}")


if __name__ == "__main__":
    main()
