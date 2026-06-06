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

DETALHADO_COLUMN_EXPRESSIONS: dict[str, str] = {
    "job_id": "={{ $json.job_id }}",
    "sku_pesquisado": "={{ $json.sku_searched }}",
    "sku_encontrado": "={{ $json.sku_found }}",
    "correspondencia_exata": "={{ $json.exact_match }}",
    "site": "={{ $json.site }}",
    "preco": "={{ $json.price }}",
    "preco-medio": "={{ $json.preco_medio }}",
    "moeda": "={{ $json.currency }}",
    "disponibilidade": "={{ $json.availability }}",
    "vendedor": "={{ $json.seller }}",
    "uf": "={{ $json.uf }}",
    "empresa": "={{ $json.empresa }}",
    "cnpj": "={{ $json.cnpj }}",
    "url_produto": "={{ $json.product_url }}",
    "origem": "={{ $json.origin }}",
    "titulo_bruto": "={{ $json.raw_title }}",
    "coletado_em": "={{ $json.scraped_at }}",
    "tempo_busca_ms": "={{ $json.search_time_ms }}",
    "condicao": "={{ $json.condition }}",
    "duracao_job_s": "={{ $json.job_duration_s }}",
    "marca": "={{ $json.brand }}",
    "codigo_site": "={{ $json.site_code }}",
    "status_resultado": "={{ $json.status_resultado }}",
    "source_health": "={{ $json.source_health }}",
    "has_valid_price": "={{ $json.has_valid_price }}",
}

DETALHADO_COLUMN_ALIASES = {
    "id_job": "job_id",
    "estado": "uf",
}

SCRAPER_DETALHADO_JS = """// CDP result flattener v1.1 — canonical result semantics.
// body may be a JSON string because the webhook uses rawBody.
let payload = $json.body;
if (typeof payload === 'string') {
  try { payload = JSON.parse(payload); } catch (e) { payload = {}; }
}
if (!payload || typeof payload !== 'object') payload = {};

const q = $json.query || {};
const jmeta = typeof payload.job_metadata === 'object' && payload.job_metadata !== null ? payload.job_metadata : {};
const skipEncontrado = String(jmeta.ad_hoc || q.ad_hoc || '').toLowerCase() === 'true';

const jobId = payload.job_id || 'unknown';
const jobDuration = payload.duration_seconds || 0;
const results = payload.results || [];
const rows = [];

function naStr(v) {
  if (v === null || v === undefined || v === '') return 'N/A';
  return typeof v === 'string' ? v : String(v);
}
function naPrice(v) {
  if (v === null || v === undefined || v === '') return 'N/A';
  if (typeof v === 'number' && !Number.isNaN(v)) return String(v);
  return String(v);
}
function toBoolPt(v) { return v ? 'SIM' : 'NAO'; }
function numericPrice(v) {
  if (v === null || v === undefined || v === '') return null;
  const n = Number(v);
  return Number.isFinite(n) && n > 0 ? n : null;
}
function hasValidPrice(part) {
  return !!(part && part.exact_match && numericPrice(part.price) !== null);
}
function normalizeSourceHealth(siteResult) {
  const explicit = String(siteResult.source_health || '').trim().toUpperCase();
  if (explicit) return explicit;
  const status = String(siteResult.status || '').toLowerCase();
  if (status === 'blocked') return 'BLOCKED';
  if (status === 'timeout') return 'TIMEOUT';
  if (status === 'error') return 'ERROR';
  if (status === 'not_queried') return 'NOT_QUERIED';
  return 'WORKING';
}
function normalizeSkuResult(siteResult, parts) {
  const explicit = String(siteResult.sku_result || '').trim().toUpperCase();
  if (explicit) return explicit;
  const health = normalizeSourceHealth(siteResult);
  if (health !== 'WORKING') return health;
  if ((parts || []).some(hasValidPrice)) return 'FOUND_PRICE';
  if (String(siteResult.status || '').toLowerCase() === 'no_price' || (parts || []).some((p) => !!p.exact_match)) return 'NO_PRICE';
  return 'NOT_FOUND';
}
function toAvailabilityPt(v) {
  const key = String(v || '').toLowerCase();
  const map = {
    in_stock: 'em_estoque',
    out_of_stock: 'fora_de_estoque',
    not_found: 'nao_encontrado',
    no_price: 'sem_preco',
    blocked: 'bloqueado',
    timeout: 'timeout',
    error: 'erro_scraper',
    scraper_error: 'erro_scraper',
    unknown: 'desconhecido',
    no_results: 'sem_resultados',
  };
  return map[key] || key || 'desconhecido';
}
function availabilityForCanonical(status, fallback) {
  const s = String(status || '').toUpperCase();
  if (s === 'FOUND_PRICE') return toAvailabilityPt(fallback || 'in_stock');
  if (s === 'NO_PRICE') return 'sem_preco';
  if (s === 'NOT_FOUND') return 'nao_encontrado';
  if (s === 'BLOCKED') return 'bloqueado';
  if (s === 'TIMEOUT') return 'timeout';
  if (s === 'ERROR') return 'erro_scraper';
  if (s === 'NOT_QUERIED') return 'sem_resultados';
  return toAvailabilityPt(fallback);
}
function rawTitleForStatus(status, message) {
  const msg = String(message || status || 'sem_resultados').trim();
  const s = String(status || '').toUpperCase();
  if (s === 'BLOCKED') return 'BLOQUEADO: ' + msg;
  if (s === 'TIMEOUT') return 'TIMEOUT: ' + msg;
  if (s === 'ERROR') return 'ERRO: ' + msg;
  if (s === 'NO_PRICE') return 'SEM_PRECO: ' + msg;
  if (s === 'NOT_FOUND') return 'NOT_FOUND';
  return msg.toUpperCase();
}
function toConditionPt(v) {
  const key = String(v || '').toLowerCase();
  if (!key || key === 'n/a') return 'N/A';
  const map = { new: 'novo', used: 'usado', refurbished: 'recondicionado', unknown: 'desconhecido' };
  return map[key] || key;
}
function placeholderRow({ sku, brand, siteResult, status }) {
  const siteCode = siteResult.site || '';
  const siteName = siteResult.site_name || siteCode;
  const canonical = normalizeSkuResult(siteResult, []);
  const health = normalizeSourceHealth(siteResult);
  const message = siteResult.blocked_reason || siteResult.error_message || status || 'sem_resultados';
  return {
    job_id: jobId,
    sku_searched: naStr(sku),
    sku_found: 'N/A',
    exact_match: toBoolPt(false),
    site: naStr(siteName),
    price: 'N/A',
    preco_medio: 'N/A',
    currency: 'N/A',
    availability: availabilityForCanonical(canonical, status),
    seller: 'N/A',
    uf: '',
    empresa: 'N/A',
    cnpj: '',
    product_url: 'N/A',
    origin: 'N/A',
    raw_title: rawTitleForStatus(canonical, message),
    scraped_at: new Date().toISOString(),
    search_time_ms: String(siteResult.search_time_ms || 0),
    job_duration_s: String(jobDuration),
    brand: naStr(brand),
    condition: 'N/A',
    site_code: naStr(siteCode),
    status_resultado: canonical,
    source_health: health,
    has_valid_price: false,
  };
}

for (const skuResult of results) {
  const sku = skuResult.sku || '';
  const brand = skuResult.brand || '';
  for (const siteResult of skuResult.site_results || []) {
    const siteName = siteResult.site_name || siteResult.site || '';
    const siteCode = siteResult.site || '';
    const siteStatus = siteResult.status || 'unknown';
    const searchTimeMs = siteResult.search_time_ms || 0;
    const parts = Array.isArray(siteResult.results) ? siteResult.results : [];

    if (parts.length === 0) {
      rows.push(placeholderRow({ sku, brand, siteResult, status: siteStatus }));
      continue;
    }

    for (const part of parts) {
      const rowHasValidPrice = hasValidPrice(part);
      const canonical = rowHasValidPrice ? 'FOUND_PRICE' : 'NO_PRICE';
      rows.push({
        job_id: jobId,
        sku_searched: naStr(part.sku_searched || sku),
        sku_found: naStr(part.sku_found),
        exact_match: toBoolPt(!!part.exact_match),
        site: naStr(siteName),
        preco_medio: 'N/A',
        price: naPrice(part.price),
        currency: part.currency || 'BRL',
        availability: availabilityForCanonical(canonical, part.availability || siteStatus || 'unknown'),
        seller: naStr(part.seller_name),
        uf: naStr(part.seller_uf || part.seller_state || ''),
        empresa: naStr(part.seller_company_name || part.seller_name),
        cnpj: naStr(part.seller_cnpj || ''),
        product_url: naStr(part.product_url),
        origin: naStr(part.origin),
        raw_title: naStr(part.raw_title),
        scraped_at: part.scraped_at || new Date().toISOString(),
        search_time_ms: String(searchTimeMs),
        job_duration_s: String(jobDuration),
        brand: naStr(brand),
        condition: toConditionPt(part.condition),
        site_code: naStr(siteCode),
        status_resultado: canonical,
        source_health: normalizeSourceHealth(siteResult),
        has_valid_price: rowHasValidPrice,
      });
    }
  }
}

if (rows.length === 0) {
  rows.push({
    job_id: jobId,
    sku_searched: 'SEM_DADOS',
    sku_found: 'N/A',
    exact_match: toBoolPt(false),
    site: 'N/A',
    price: 'N/A',
    preco_medio: 'N/A',
    currency: 'N/A',
    availability: toAvailabilityPt('no_results'),
    seller: 'N/A',
    uf: '',
    empresa: 'N/A',
    cnpj: '',
    product_url: 'N/A',
    origin: 'N/A',
    raw_title: 'Sem resultados de scraping',
    scraped_at: new Date().toISOString(),
    search_time_ms: '0',
    job_duration_s: String(jobDuration),
    brand: 'N/A',
    condition: 'N/A',
    site_code: 'N/A',
    status_resultado: 'NOT_QUERIED',
    source_health: 'NOT_QUERIED',
    has_valid_price: false,
  });
}

return rows.map((row) => ({ json: { ...row, _skip_encontrado: skipEncontrado } }));
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

function numericPrice(v) {
  if (v === null || v === undefined || v === '') return null;
  const n = Number(v);
  return Number.isFinite(n) && n > 0 ? n : null;
}

function partHasValidPrice(part) {
  return !!(part && part.exact_match && numericPrice(part.price) !== null);
}

function siteHasValidPrice(siteResult) {
  if (siteResult.has_valid_price === true) return true;
  return (Array.isArray(siteResult.results) ? siteResult.results : []).some(partHasValidPrice);
}

function skuHasValidPrice(skuResult) {
  if (skuResult.has_valid_price === true || String(skuResult.sku_result || '').toUpperCase() === 'FOUND_PRICE') return true;
  const best = skuResult.best_price || null;
  if (best && best.exact_match !== false && numericPrice(best.price) !== null) return true;
  return (Array.isArray(skuResult.site_results) ? skuResult.site_results : []).some(siteHasValidPrice);
}

function skuHasNoPriceEvidence(skuResult) {
  if (skuResult.has_any_exact_evidence === true) return true;
  return (Array.isArray(skuResult.site_results) ? skuResult.site_results : []).some((sr) => {
    const parts = Array.isArray(sr.results) ? sr.results : [];
    return String(sr.sku_result || '').toUpperCase() === 'NO_PRICE'
      || String(sr.status || '').toLowerCase() === 'no_price'
      || parts.some((part) => !!part.exact_match);
  });
}

function canonicalSkuStatus(skuResult) {
  const explicit = String(skuResult.sku_result || '').trim().toUpperCase();
  if (explicit) return explicit;
  const statuses = siteStatuses(skuResult);
  if (skuHasValidPrice(skuResult)) return 'FOUND_PRICE';
  if (statuses.includes('blocked')) return 'BLOCKED';
  if (statuses.includes('timeout') || statuses.includes('error')) return 'ERROR';
  if (skuHasNoPriceEvidence(skuResult) || statuses.includes('no_price')) return 'NO_PRICE';
  return 'NOT_FOUND';
}

function sheetStatusForCanonical(canonical) {
  if (canonical === 'FOUND_PRICE') return STATUS.FOUND;
  if (canonical === 'NO_PRICE') return STATUS.NO_PRICE;
  if (canonical === 'BLOCKED') return STATUS.BLOCKED;
  if (canonical === 'TIMEOUT' || canonical === 'ERROR') return '⚠️ Erro';
  return STATUS.NOT_FOUND;
}

const wh = $('🔔 Webhook: Receber Resultados').first().json;
const payload = parseBody(wh.body);

const skipEncontrado = false;
const results = Array.isArray(payload.results) ? payload.results : [];
const rows = [];

for (const skuResult of results) {
  const sku = skuResult.sku || '';
  const canonical = canonicalSkuStatus(skuResult);

  let bestPrice = null;
  let bestSite = '';
  let bestUrl = '';
  const best = skuResult.best_price || null;
  if (best && best.exact_match !== false && numericPrice(best.price) !== null) {
    bestPrice = numericPrice(best.price);
    bestSite = best.site_name || best.site || '';
    bestUrl = best.product_url || '';
  }
  for (const sr of skuResult.site_results || []) {
    for (const part of sr.results || []) {
      if (partHasValidPrice(part)) {
        const price = numericPrice(part.price);
        if (!bestPrice || price < bestPrice) {
          bestPrice = price;
          bestSite = sr.site_name || sr.site || '';
          bestUrl = part.product_url || '';
        }
      }
    }
  }

  if (!bestSite && skuHasNoPriceEvidence(skuResult)) {
    for (const sr of skuResult.site_results || []) {
      for (const part of sr.results || []) {
        const u = String(part.product_url || '').trim();
        if (part.exact_match && u) {
          bestSite = sr.site_name || sr.site || '';
          bestUrl = u;
          break;
        }
      }
      if (bestSite) break;
    }
  }

  const status = sheetStatusForCanonical(canonical);

  let melhor = 'N/A';
  if (bestPrice) {
    melhor = 'R$ ' + bestPrice.toLocaleString('pt-BR', { minimumFractionDigits: 2 });
  } else if (canonical === 'NO_PRICE') {
    melhor = 'S/ preço (ver Detalhado)';
  } else if (canonical === 'BLOCKED') {
    melhor = 'Bloqueado';
  } else if (canonical === 'TIMEOUT' || canonical === 'ERROR') {
    melhor = 'Erro';
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

SCRAPER_HISTORICO_JS = """function parseBody(raw) {
  let p = raw;
  if (typeof p === 'string') {
    try { p = JSON.parse(p); } catch (e) { p = {}; }
  }
  return p && typeof p === 'object' ? p : {};
}
const wh = $('🔔 Webhook: Receber Resultados').first().json;
const q = wh.query || {};
const meta = parseBody(wh.body);
const items = meta.results || [];
const errs = meta.errors || [];
const jm = typeof meta.job_metadata === 'object' && meta.job_metadata !== null ? meta.job_metadata : {};

let job_error = '';
if (errs.length) job_error = errs.join(' | ');
if (meta.warning_messages && meta.warning_messages.length) {
  job_error = job_error ? job_error + ' | ' : '';
  job_error += meta.warning_messages.join(' | ');
}
const dupCsv = String(jm.duplicate_skus_csv || q.duplicate_skus_csv || '').trim();
const dupCount = Number(jm.duplicates_count || (dupCsv ? dupCsv.split(',').filter(Boolean).length : 0));
if (dupCount > 0) {
  const dupMsg = `SKUs repetidos: ${dupCount}${dupCsv ? ' (' + dupCsv + ')' : ''}`;
  job_error = job_error ? job_error + ' | ' + dupMsg : dupMsg;
}
if (!job_error) job_error = '—';

const skus_csv = [...new Set(items.map((s) => String(s.sku || '').trim()).filter(Boolean))].join(', ');
const dur = meta.duration_seconds != null ? Number(meta.duration_seconds) : 0;
const notify = String(jm.notify || q.notify || 'none').toLowerCase();
const origem = notify === 'telegram' ? 'telegram' : notify === 'email' ? 'email' : 'auto';
const solicitante = String(jm.reply_email || q.reply_email || jm.chat_id || q.chat_id || '').trim() || '—';
const disparado_em = meta.started_at
  ? String(meta.started_at)
  : new Date(Date.now() - dur * 1000).toISOString();
const concluido_em = meta.completed_at ? String(meta.completed_at) : new Date().toISOString();
const totalItems = Number(meta.total_items || jm.total_read || items.length || 0);
const skus_validos = totalItems > 0 ? totalItems : Number(jm.valid_skus || items.length || 0);

function partHasValidPrice(part) {
  const n = Number(part?.price);
  return !!(part && part.exact_match && Number.isFinite(n) && n > 0);
}
function siteHasValidPrice(sr) {
  if (sr.has_valid_price === true) return true;
  return (Array.isArray(sr.results) ? sr.results : []).some(partHasValidPrice);
}
function siteHasNoPriceEvidence(sr) {
  const parts = Array.isArray(sr.results) ? sr.results : [];
  return String(sr.sku_result || '').toUpperCase() === 'NO_PRICE'
    || String(sr.status || '').toLowerCase() === 'no_price'
    || parts.some((part) => !!part.exact_match);
}
function skuHasValidPrice(skuResult) {
  if (skuResult.has_valid_price === true || String(skuResult.sku_result || '').toUpperCase() === 'FOUND_PRICE') return true;
  const best = skuResult.best_price || null;
  if (best && best.exact_match !== false) {
    const n = Number(best.price);
    if (Number.isFinite(n) && n > 0) return true;
  }
  return (Array.isArray(skuResult.site_results) ? skuResult.site_results : []).some(siteHasValidPrice);
}
function skuHasNoPriceEvidence(skuResult) {
  if (skuResult.has_any_exact_evidence === true || String(skuResult.sku_result || '').toUpperCase() === 'NO_PRICE') return true;
  return (Array.isArray(skuResult.site_results) ? skuResult.site_results : []).some(siteHasNoPriceEvidence);
}
function numberOrNull(value) {
  if (value === null || value === undefined || value === '') return null;
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

const pricedSkusFromPayload = numberOrNull(meta.priced_sku_count);
const evidenceSkusFromPayload = numberOrNull(meta.any_evidence_sku_count ?? meta.sku_success_count);
const noPriceSkusFromPayload = numberOrNull(meta.no_price_sku_count);
const blockedSkusFromPayload = numberOrNull(meta.blocked_sku_count);
const errorSkusFromPayload = numberOrNull(meta.error_sku_count);
const notFoundSkusFromPayload = numberOrNull(meta.all_sites_not_found_count);
const pricedSkus = pricedSkusFromPayload ?? items.filter(skuHasValidPrice).length;
const evidenceSkus = evidenceSkusFromPayload ?? items.filter((item) => skuHasValidPrice(item) || skuHasNoPriceEvidence(item)).length;
const noPriceSkus = noPriceSkusFromPayload ?? Math.max(0, items.filter(skuHasNoPriceEvidence).length - pricedSkus);
const blockedSkus = blockedSkusFromPayload ?? items.filter((item) =>
  (item.site_results || []).some((sr) => String(sr.sku_result || sr.status || '').toUpperCase() === 'BLOCKED' || String(sr.status || '').toLowerCase() === 'blocked')
).length;
const errorSkus = errorSkusFromPayload ?? items.filter((item) =>
  (item.site_results || []).some((sr) => ['TIMEOUT', 'ERROR'].includes(String(sr.sku_result || '').toUpperCase()) || ['timeout', 'error'].includes(String(sr.status || '').toLowerCase()))
).length;
const notFoundSkus = notFoundSkusFromPayload ?? Math.max(0, skus_validos - evidenceSkus - blockedSkus - errorSkus);
const skuHit = skus_validos > 0 ? ((pricedSkus / skus_validos) * 100).toFixed(1) + '%' : '0.0%';
const status =
  errs.length > 0 || errorSkus > 0
    ? '❌ ERRO_JOB'
    : blockedSkus > 0 || noPriceSkus > 0 || notFoundSkus > 0
      ? '⚠️ AVISOS'
      : '✅ CONCLUIDO';

const siteTotals = {};
let checks = 0;
let hits = 0;
for (const skuResult of items) {
  for (const sr of (skuResult.site_results || [])) {
    const key = String(sr.site || sr.site_name || 'site').trim() || 'site';
    checks += 1;
    if (!siteTotals[key]) siteTotals[key] = { total: 0, hits: 0 };
    siteTotals[key].total += 1;
    if (siteHasValidPrice(sr)) {
      hits += 1;
      siteTotals[key].hits += 1;
    }
  }
}
const taxaSite = checks > 0 ? ((hits / checks) * 100).toFixed(1) + '%' : 'N/A';
const resumoSitesObj = {};
for (const [k, v] of Object.entries(siteTotals)) {
  resumoSitesObj[k] = v.total > 0 ? Number(((v.hits / v.total) * 100).toFixed(1)) : 0;
}

return [{
  json: {
    job_id: meta.job_id || 'unknown',
    origem,
    solicitante,
    disparado_em,
    concluido_em,
    tempo_segundos: dur,
    status,
    skus_lidos: totalItems,
    skus_validos,
    skus_encontrados: pricedSkus,
    skus_falhos: notFoundSkus + blockedSkus + errorSkus,
    taxa_sucesso_sku: skuHit,
    taxa_sucesso_sites: taxaSite,
    sites_pesquisados: Object.keys(siteTotals).length || 5,
    resumo_sites: JSON.stringify({
      ...resumoSitesObj,
      no_price: noPriceSkus,
      not_found: notFoundSkus,
      blocked: blockedSkus,
      error: errorSkus,
    }),
    lista_skus_csv: skus_csv || '—',
    skus_repetidos: dupCsv || '—',
    job_error,
  },
}];
"""


BULK_EXPORT_JS = """
// Bulk spreadsheet export v1.2 — found means FOUND_PRICE only.
function parseBody(raw) {
  let p = raw;
  if (typeof p === 'string') { try { p = JSON.parse(p); } catch (e) { p = {}; } }
  return p && typeof p === 'object' ? p : {};
}
function env(name) {
  try { if (typeof process !== 'undefined' && process.env && process.env[name]) return String(process.env[name]).trim(); } catch (e) {}
  return '';
}
function workflowName() {
  try {
    if (typeof $workflow !== 'undefined' && $workflow && $workflow.name) return String($workflow.name);
  } catch (e) {}
  return '';
}
function isDevWorkflow() {
  return workflowName().trim().toLowerCase().startsWith('dev -') || env('CDP_ENV').toLowerCase() === 'dev';
}
function envFor(name) {
  if (isDevWorkflow() && name === 'CDP_RESULTADOS_SHEETS_URL') return env('CDP_DEV_RESULTADOS_SHEETS_URL');
  return env(name);
}
function numericPrice(v) {
  if (v === null || v === undefined || v === '') return null;
  const n = Number(v);
  return Number.isFinite(n) && n > 0 ? n : null;
}
function partHasValidPrice(part) {
  return !!(part && part.exact_match && numericPrice(part.price) !== null);
}
function siteHasValidPrice(sr) {
  if (sr.has_valid_price === true || String(sr.sku_result || '').toUpperCase() === 'FOUND_PRICE') return true;
  return (Array.isArray(sr.results) ? sr.results : []).some(partHasValidPrice);
}
function siteHasNoPriceEvidence(sr) {
  const parts = Array.isArray(sr.results) ? sr.results : [];
  return String(sr.sku_result || '').toUpperCase() === 'NO_PRICE'
    || String(sr.status || '').toLowerCase() === 'no_price'
    || parts.some((part) => !!part.exact_match);
}
function skuHasValidPrice(skuResult) {
  if (skuResult.has_valid_price === true || String(skuResult.sku_result || '').toUpperCase() === 'FOUND_PRICE') return true;
  const best = skuResult.best_price || null;
  if (best && best.exact_match !== false && numericPrice(best.price) !== null) return true;
  return (Array.isArray(skuResult.site_results) ? skuResult.site_results : []).some(siteHasValidPrice);
}
function canonicalSkuStatus(skuResult) {
  const explicit = String(skuResult.sku_result || '').trim().toUpperCase();
  if (explicit) return explicit;
  const sites = Array.isArray(skuResult.site_results) ? skuResult.site_results : [];
  const statuses = sites.map((sr) => String(sr.status || '').toLowerCase());
  if (skuHasValidPrice(skuResult)) return 'FOUND_PRICE';
  if (statuses.includes('blocked')) return 'BLOCKED';
  if (statuses.includes('timeout') || statuses.includes('error')) return 'ERROR';
  if (skuResult.has_any_exact_evidence === true || sites.some(siteHasNoPriceEvidence)) return 'NO_PRICE';
  return 'NOT_FOUND';
}
function bestExactOffer(skuResult) {
  let bestPrice = null;
  let bestSite = '';
  let bestUrl = '';
  const best = skuResult.best_price || null;
  if (best && best.exact_match !== false && numericPrice(best.price) !== null) {
    bestPrice = numericPrice(best.price);
    bestSite = best.site_name || best.site || '';
    bestUrl = best.product_url || '';
  }
  for (const sr of skuResult.site_results || []) {
    for (const part of sr.results || []) {
      if (!partHasValidPrice(part)) continue;
      const price = numericPrice(part.price);
      if (bestPrice === null || price < bestPrice) {
        bestPrice = price;
        bestSite = sr.site_name || sr.site || '';
        bestUrl = part.product_url || '';
      }
    }
  }
  return { bestPrice, bestSite, bestUrl };
}
function statusLabel(status) {
  if (status === 'FOUND_PRICE') return 'Encontrado';
  if (status === 'NO_PRICE') return 'Sem preco';
  if (status === 'BLOCKED') return 'Bloqueado';
  if (status === 'TIMEOUT' || status === 'ERROR') return 'Erro';
  return 'Sem resultado';
}
function csvEscape(val) {
  const s = String(val ?? '');
  if (/[;\\r\\n"]/.test(s)) return '"' + s.replace(/"/g, '""') + '"';
  return s;
}

const notifData = $('📣 Formatar Notificação Conclusão').first().json;
const wh = $('🔔 Webhook: Receber Resultados').first().json;
const payload = parseBody(wh.body);
const jm = typeof payload.job_metadata === 'object' && payload.job_metadata !== null ? payload.job_metadata : {};

const jobId = payload.job_id || 'unknown';
let notify = notifData.notify || 'none';
let replyChannel = String(
  jm.reply_channel || jm.command_origin || notifData.reply_channel || notifData.origem || ''
).trim().toLowerCase();
const origem = notifData.origem || 'auto';
let chatId = String(notifData.telegram_chat_id || jm.chat_id || '').trim();
let replyEmail = notifData.email_to || jm.reply_email || '';
if (!replyChannel) {
  if (notify === 'email' || replyEmail) replyChannel = 'email';
  else if (notify === 'telegram' || chatId) replyChannel = 'telegram';
}
if (replyChannel === 'email') {
  notify = 'email';
  chatId = '';
} else if (replyChannel === 'telegram') {
  notify = 'telegram';
  replyEmail = '';
}
const results = Array.isArray(payload.results) ? payload.results : [];
const total = Number(payload.total_items || results.length || 0);
const evidence = Number(payload.any_evidence_sku_count ?? payload.sku_success_count ?? 0);
const found = Number(payload.priced_sku_count ?? 0);
const noPrice = Number(payload.no_price_sku_count ?? Math.max(0, evidence - found));
const blocked = Number(payload.blocked_sku_count ?? 0);
const errors = Number(payload.error_sku_count ?? 0);
const notFound = Number(payload.all_sites_not_found_count ?? Math.max(0, total - evidence - blocked - errors));
const pct = total > 0 ? ((found / total) * 100).toFixed(1) : '0.0';
const dur = Number(payload.duration_seconds ?? 0);
const startedAt = payload.started_at || new Date(Date.now() - dur * 1000).toISOString();
const completedAt = payload.completed_at || new Date().toISOString();
const configuredSheetsUrl = envFor('CDP_RESULTADOS_SHEETS_URL');
const sheetsUrl = configuredSheetsUrl || (isDevWorkflow()
  ? ''
  : 'https://docs.google.com/spreadsheets/d/1O6H__UGqja7FZsQkA-WcePKtbKS-bcb5XFzmbJTrhPw/edit');

const rows = [];
for (const skuResult of results) {
  const sku = skuResult.sku || '';
  const canonical = canonicalSkuStatus(skuResult);
  const offer = canonical === 'FOUND_PRICE' ? bestExactOffer(skuResult) : { bestPrice: null, bestSite: '', bestUrl: '' };
  const siteSummary = [];
  for (const sr of skuResult.site_results || []) {
    const siteName = sr.site_name || sr.site || '';
    const srStatus = String(sr.sku_result || sr.status || '').toLowerCase() || 'sem_resultado';
    siteSummary.push(siteName + (siteHasValidPrice(sr) ? ' OK' : ' ' + srStatus));
  }
  rows.push({
    SKU: sku,
    STATUS: statusLabel(canonical),
    'MELHOR PREÇO': offer.bestPrice !== null
      ? 'BRL ' + Number(offer.bestPrice).toLocaleString('pt-BR', { minimumFractionDigits: 2 })
      : 'N/A',
    SITE: offer.bestSite || 'N/A',
    LINK: offer.bestUrl || 'N/A',
    'SITES CHECADOS': siteSummary.join(' | '),
    DATA: new Date().toLocaleDateString('pt-BR'),
  });
}

const header = ['SKU','STATUS','MELHOR PREÇO','SITE','LINK','SITES CHECADOS','DATA'];
const csvLines = [header.map(csvEscape).join(';')];
for (const r of rows) csvLines.push(header.map((h) => csvEscape(r[h] ?? '')).join(';'));
const csvText = '\\ufeff' + csvLines.join('\\r\\n');
const b64 = Buffer.from(csvText, 'utf8').toString('base64');
const fname = `cdp_${jobId}_${new Date().toISOString().slice(0,10)}.csv`;
const durStr = dur >= 60 ? `${Math.floor(dur / 60)}m ${Math.round(dur % 60)}s` : `${Math.round(dur)}s`;

return [{
  json: {
    notify, origem, chatId, replyEmail, sheetsUrl,
    jobId, total, found, noPrice, notFound, blocked, errors, pct, durStr,
    startedAt, completedAt,
    filename: fname,
    file_b64: b64,
    xlsx_b64: b64,
    _notify_ok: true,
  },
  binary: {
    data: {
      data: b64,
      mimeType: 'text/csv; charset=utf-8',
      fileName: fname,
      fileExtension: 'csv',
    },
  },
}];
"""

BULK_CAPTION_JS = """const d = $input.first().json;
const lines = [
  '🤖 *Assistente CDP*',
  '',
  '✅ *WEBSCRAPERS: busca concluída*',
  '',
  '📊 *' + d.found + '* de *' + d.total + '* com preço encontrado',
];
if (Number(d.noPrice || 0) > 0) lines.push('⚠️ Sem preço: *' + d.noPrice + '*');
if (Number(d.notFound || 0) > 0) lines.push('⚠️ Sem resultado: *' + d.notFound + '*');
if (Number(d.blocked || 0) > 0) lines.push('🚫 Bloqueados: *' + d.blocked + '*');
if (Number(d.errors || 0) > 0) lines.push('⚠️ Erros/timeouts: *' + d.errors + '*');
lines.push('📎 Relatório: ' + d.sheetsUrl);
return [{ json: { ...d, caption: lines.join('\\n') }, binary: $input.first().binary }];
"""

BULK_EMAIL_JS = """
const d = $input.first().json;
const pct = Number(d.pct || 0);
const bar = Math.min(100, Math.max(0, Math.round(pct)));
const isGood = Number(d.found || 0) > 0 && Number(d.blocked || 0) === 0 && Number(d.errors || 0) === 0;
const html = `<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="UTF-8">
<style>
  body{font-family:Arial,sans-serif;background:#f4f4f4;margin:0;padding:20px}
  .wrap{background:#fff;border-radius:8px;padding:32px;max-width:640px;margin:auto;box-shadow:0 2px 10px rgba(0,0,0,.1)}
  h1{color:#111827;font-size:22px;margin:0 0 6px}.badge{display:inline-block;padding:3px 10px;border-radius:4px;font-size:12px;font-weight:700;margin-bottom:20px;background:${isGood?'#16a34a':'#f59e0b'};color:#fff}
  h2{font-size:13px;text-transform:uppercase;color:#6b7280;border-bottom:1px solid #e5e7eb;padding-bottom:5px;margin:22px 0 10px}
  .row{display:flex;justify-content:space-between;padding:5px 0;font-size:14px}.lbl{color:#6b7280}.val{font-weight:600;color:#111827}
  .grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:12px 0}.box{background:#f9fafb;border-radius:6px;padding:14px 16px}
  .num{font-size:26px;font-weight:700;color:#111827}.g{color:#16a34a}.w{color:#b45309}.r{color:#dc2626}.sub{font-size:12px;color:#6b7280;margin-top:2px}
  .bar-bg{height:10px;background:#e5e7eb;border-radius:99px;overflow:hidden;margin:8px 0}.bar-fill{height:100%;background:${isGood?'#16a34a':'#f59e0b'};width:${bar}%;border-radius:99px}
  .btn{display:inline-block;background:#2563eb;color:#fff;padding:12px 24px;border-radius:6px;text-decoration:none;font-weight:700;font-size:14px;margin-top:18px}
  .foot{text-align:center;font-size:11px;color:#9ca3af;margin-top:28px}code{background:#f3f4f6;padding:1px 6px;border-radius:3px;font-size:12px}
</style></head>
<body><div class="wrap">
  <h1>WEBSCRAPERS: busca concluída</h1>
  <span class="badge">${isGood ? 'Com preço encontrado' : 'Atenção'}</span>
  <p style="font-size:14px;color:#374151;margin:0 0 14px">A busca nos sites públicos foi finalizada. Este é o resultado de <strong>WEBSCRAPERS</strong>; <strong>ESTOQUE ONLINE</strong> chega em e-mail separado quando a consulta de estoque terminar.</p>
  <h2>Metadados do Job</h2>
  <div class="row"><span class="lbl">Job ID</span><span class="val"><code>${d.jobId}</code></span></div>
  <div class="row"><span class="lbl">Início</span><span class="val">${d.startedAt}</span></div>
  <div class="row"><span class="lbl">Conclusão</span><span class="val">${d.completedAt}</span></div>
  <div class="row"><span class="lbl">Duração</span><span class="val">${d.durStr}</span></div>
  <h2>Resultados</h2>
  <div class="grid">
    <div class="box"><div class="num">${d.total}</div><div class="sub">SKUs processados</div></div>
    <div class="box"><div class="num g">${d.found}</div><div class="sub">Com preço encontrado</div></div>
    <div class="box"><div class="num w">${d.noPrice}</div><div class="sub">Sem preço</div></div>
    <div class="box"><div class="num r">${d.notFound}</div><div class="sub">Sem resultado</div></div>
    <div class="box"><div class="num r">${d.blocked}</div><div class="sub">Bloqueados</div></div>
    <div class="box"><div class="num r">${d.errors}</div><div class="sub">Erros/timeouts</div></div>
  </div>
  <div style="font-size:13px;color:#374151;margin-top:8px"><strong>Taxa com preço: ${d.pct}%</strong></div>
  <div class="bar-bg"><div class="bar-fill"></div></div>
  <h2>Acessar resultados</h2>
  <p style="font-size:14px;color:#374151">Os resultados de WEBSCRAPERS estão no Google Sheets e em anexo neste e-mail.</p>
  <a href="${d.sheetsUrl}" class="btn">Abrir Google Sheets</a>
  <div class="foot">Mensagem automática do Assistente CDP · ${new Date().toLocaleString('pt-BR',{timeZone:'America/Sao_Paulo'})}</div>
</div></body></html>`;

const subject = `Assistente CDP - WEBSCRAPERS: busca concluída (${d.found}/${d.total} com preço, ${d.pct}%)`;
return [{ json: { ...d, email_html: html, email_subject: subject }, binary: $input.first().binary }];
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


def patch_detalhado_columns(wf: dict) -> None:
    for node in wf["nodes"]:
        if node.get("name") != "📊 Salvar → CDP_Resultados (Detalhado)":
            continue
        cols = node["parameters"]["columns"]
        value = dict(cols.get("value") or {})
        normalized: dict[str, str] = {}
        for key, expr in value.items():
            canonical = DETALHADO_COLUMN_ALIASES.get(key, key)
            normalized.setdefault(canonical, expr)

        ordered = {
            key: normalized.get(key, expr)
            for key, expr in DETALHADO_COLUMN_EXPRESSIONS.items()
        }
        for key, expr in normalized.items():
            if key.startswith("melibox_"):
                continue
            if key not in ordered:
                ordered[key] = expr
        cols["value"] = ordered


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
        if name == "📊 Extrair Dados (Detalhado)":
            node["parameters"]["jsCode"] = SCRAPER_DETALHADO_JS
        elif name == "📋 Extrair Resumo":
            node["parameters"]["jsCode"] = SCRAPER_RESUMO_JS
        elif name == "📊 Construir Relatório Histórico":
            node["parameters"]["jsCode"] = SCRAPER_HISTORICO_JS
        elif name == "📝 Salvar → CDP_Resultados (Histórico)":
            node["notes"] = (
                "Appends to 'Historico'. skus_encontrados/taxa_sucesso_sku use priced_sku_count "
                "(FOUND_PRICE) only; NO_PRICE/NOT_FOUND/BLOCKED/ERROR stay separate in resumo_sites."
            )
        elif name == "🗂️ Gerar Excel Bulk":
            node["parameters"]["jsCode"] = BULK_EXPORT_JS
            node["notes"] = (
                "CDP v1.2: builds UTF-8 CSV from canonical result semantics; "
                "found means FOUND_PRICE only."
            )
        elif name == "📱 Formatar Caption Bulk (Telegram)":
            node["parameters"]["jsCode"] = BULK_CAPTION_JS
        elif name == "📧 Formatar HTML Bulk (Email)":
            node["parameters"]["jsCode"] = BULK_EMAIL_JS
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
    patch_detalhado_columns(wf)
    patch_rownum_markers(wf)
    WF_PATH.write_text(json.dumps(wf, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Patched {WF_PATH}")


if __name__ == "__main__":
    main()
