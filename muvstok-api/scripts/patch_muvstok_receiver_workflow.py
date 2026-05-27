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
    _encontrado: '✅ Encontrado',
  };
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
  else if (found) status = '⚠️ Encontrado (sem preço)';
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
    node = next(n for n in wf["nodes"] if n["name"] == "✅ Atualizar CDP_SKUs")
    cols = node["parameters"]["columns"]
    cols["value"] = {
        "CODIGO": "={{ $json.sku }}",
        "PROCESSADO": "={{ $json.PROCESSADO }}",
        "ENCONTRADO": "={{ $json.ENCONTRADO }}",
    }
    cols["matchingColumns"] = ["CODIGO"]
    schema = cols.get("schema") or []
    if schema:
        for entry in schema:
            if entry.get("id") == "SKU":
                entry["id"] = "CODIGO"
                entry["displayName"] = "CODIGO"
        cols["matchingColumns"] = ["CODIGO"]
        cols["schema"] = [
            e if e.get("id") != "SKU" else {**e, "id": "CODIGO", "displayName": "CODIGO"}
            for e in schema
        ]
    else:
        cols["schema"] = [
            {
                "id": "CODIGO",
                "displayName": "CODIGO",
                "required": False,
                "defaultMatch": True,
                "display": True,
                "type": "string",
                "canBeUsedToMatch": True,
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
