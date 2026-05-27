// Shared helpers for n8n API Diversos receiver Code nodes (Detalhado + Resumo).
// Injected by scripts/patch_muvstok_receiver_workflow.py — do not edit workflow JSON by hand.

/** User-facing labels written to Google Sheets (not internal webhook paths). */
const CDP_SITE_CODE = 'api-diversos';
const CDP_SITE_LABEL = 'API Diversos';
const CDP_ORIGEM_LABEL = 'API Diversos';

/**
 * tipoEstoque codes written to sheet column melibox_tipo (and titulo_bruto suffix).
 * NEW=0, VIVO=1, DORMENTE=2, MORTO=3, ESCRAPE=4
 */
const STOCK_TYPE_CODE_BY_NAME = {
  new: 0,
  novo: 0,
  vivo: 1,
  dormente: 2,
  morto: 3,
  escrape: 4,
  scrape: 4,
};

function pickField(row, ...keys) {
  if (!row || typeof row !== 'object') return null;
  for (const k of keys) {
    const v = row[k];
    if (v !== null && v !== undefined && v !== '') return v;
  }
  return null;
}

function readEnv(name) {
  try {
    const fromN8n = typeof $env !== 'undefined' ? $env[name] : undefined;
    if (fromN8n !== undefined && fromN8n !== null && String(fromN8n).trim()) {
      return String(fromN8n).trim();
    }
  } catch (e) {}
  try {
    if (typeof process !== 'undefined' && process.env && process.env[name]) {
      return String(process.env[name]).trim();
    }
  } catch (e) {}
  return '';
}

function stockQty(row) {
  if (!row || typeof row !== 'object') return 0;
  const raw = pickField(
    row,
    'qtdeEstoque',
    'qtdEstoque',
    'quantidadeEstoque',
    'quantidade',
    'qtde',
    'qtd',
    'stock_quantity',
    'estoque'
  );
  const n = Number(raw);
  return Number.isFinite(n) ? n : 0;
}

function isEmEstoque(row) {
  return stockQty(row) >= 1;
}

function filterInStock(listings) {
  return (Array.isArray(listings) ? listings : []).filter((row) => isEmEstoque(row));
}

function parsePrice(v) {
  if (v === null || v === undefined || v === '') return null;
  const n = Number(v);
  if (Number.isFinite(n) && n > 0) return n;
  const s = String(v).trim().replace(/\s/g, '');
  const br = s.replace(/\./g, '').replace(',', '.');
  const n2 = Number(br);
  return Number.isFinite(n2) && n2 > 0 ? n2 : null;
}

function salePriceFromRow(row) {
  return parsePrice(
    pickField(row, 'valorPrecoVenda', 'valorprecovenda', 'valorprecavenda', 'price', 'preco')
  );
}

function costPriceFromRow(row) {
  return parsePrice(
    pickField(row, 'valorCustoMedio', 'valorcustomedio', 'average_cost', 'custo')
  );
}

function rowHasAnyPrice(row) {
  return salePriceFromRow(row) !== null || costPriceFromRow(row) !== null;
}

/** Rows used for best-price: in-stock first; else any row with sale or cost price. */
function rowsForPricing(listings) {
  const arr = Array.isArray(listings) ? listings : [];
  const inStock = filterInStock(arr);
  if (inStock.length) return inStock;
  return arr.filter((row) => row && typeof row === 'object' && rowHasAnyPrice(row));
}

function normalizeStockTypeKey(raw) {
  return String(raw)
    .trim()
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '');
}

/** Sheet value: 0–4 as string, or '' if unknown. */
function stockTypeCode(row) {
  const raw = pickField(row, 'tipoEstoque', 'tipoestoque', 'stock_type');
  if (raw === null || raw === undefined || raw === '') return '';
  const n = Number(raw);
  if (Number.isFinite(n) && n >= 0 && n <= 4) return String(Math.round(n));
  const key = normalizeStockTypeKey(raw);
  if (key in STOCK_TYPE_CODE_BY_NAME) return String(STOCK_TYPE_CODE_BY_NAME[key]);
  return '';
}

function formatPriceBr(n) {
  if (n === null || n === undefined || !Number.isFinite(n)) return '';
  return Number(n).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

/** Detalhado preco = valorPrecoVenda (always; no tipoEstoque rule). */
function naSalePriceFromRow(row) {
  const p = salePriceFromRow(row);
  if (p === null) return '';
  return formatPriceBr(p);
}

/** Detalhado preco-medio = valorCustoMedio. */
function naCostPriceFromRow(row) {
  const p = costPriceFromRow(row);
  if (p === null) return '';
  return formatPriceBr(p);
}

function formatResumoPreco(n) {
  if (n === null || n === undefined || !Number.isFinite(n)) return 'N/A';
  return 'R$ ' + formatPriceBr(n);
}

function branchLabel(row) {
  return String(
    pickField(row, 'nomeFilial', 'nomefilial', 'branch_name', 'apelidoFilial', 'apelidofilial') || ''
  ).trim();
}

function brandLabel(row) {
  return String(
    pickField(row, 'fabricante', 'montadora', 'automaker', 'marca', 'brand') || ''
  ).trim();
}

function productTitle(row) {
  const name = String(pickField(row, 'produto', 'product_name', 'descricao') || '').trim();
  const tipoCode = stockTypeCode(row);
  if (!tipoCode) return name;
  if (!name) return '[' + tipoCode + ']';
  return name + ' [' + tipoCode + ']';
}

/** API Diversos has no product URL — Detalhado url_produto and Resumo LINK stay empty. */
function productUrlForSheet(_sku, _row) {
  return '';
}

/** @deprecated — seller contact no longer written to sheets */
function buildContactInfo(_sku, _row) {
  return productUrlForSheet();
}

/** @deprecated */
function buildProductUrl(sku, row) {
  return productUrlForSheet(sku, row);
}

function buildDemandUrl(sku) {
  const base = (
    readEnv('MUVSTOK_BASE_URL') ||
    readEnv('CDP_MUVSTOK_DEMAND_BASE') ||
    'https://data-bi.muvstok.com.br/api/Demand'
  )
    .trim()
    .replace(/\/+$/, '');
  const code = String(sku || '').trim();
  return code ? base + '/?sku=' + encodeURIComponent(code) : base;
}

function parseIsoMs(value) {
  if (!value) return NaN;
  const s = String(value).trim();
  if (!s) return NaN;
  const normalized = s.includes('T') ? s.replace('Z', '+00:00') : s;
  const ms = Date.parse(normalized);
  return Number.isFinite(ms) ? ms : NaN;
}

function resolveJobDurationSeconds(payload, meta, completedAt, startedAt) {
  const fromApi = Number(payload?.duration_seconds);
  if (Number.isFinite(fromApi) && fromApi > 0) {
    return Math.round(fromApi * 100) / 100;
  }
  const endMs = parseIsoMs(completedAt || payload?.completed_at);
  const startMs = parseIsoMs(
    startedAt || payload?.started_at || meta?.dispatched_at || meta?.processing_started_at
  );
  if (Number.isFinite(endMs) && Number.isFinite(startMs) && endMs >= startMs) {
    return Math.round(((endMs - startMs) / 1000) * 100) / 100;
  }
  return 0;
}

function skuSearchTimeMs(skuResult) {
  const ms = Number(skuResult?.duration_ms);
  return Number.isFinite(ms) && ms >= 0 ? Math.round(ms) : 0;
}

/** Resumo MELHOR PREÇO = lowest valorPrecoVenda across priced in-stock rows. */
function bestOfferFromListings(listings) {
  const priced = rowsForPricing(listings);
  let bestPrice = null;
  let bestSite = '';
  for (const row of priced) {
    if (!row || typeof row !== 'object') continue;
    const p = salePriceFromRow(row);
    if (p === null) continue;
    if (bestPrice === null || p < bestPrice) {
      bestPrice = p;
      bestSite = branchLabel(row) || CDP_SITE_LABEL;
    }
  }
  return { bestPrice, bestSite };
}
