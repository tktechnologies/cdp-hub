// Shared helpers for n8n API Diversos receiver Code nodes (Detalhado + Resumo).
// Injected by scripts/patch_muvstok_receiver_workflow.py — do not edit workflow JSON by hand.

/** User-facing labels written to Google Sheets (not internal webhook paths). */
const CDP_SITE_CODE = 'api-diversos';
const CDP_SITE_LABEL = 'API Diversos';
const CDP_ORIGEM_LABEL = 'API Diversos';

/**
 * tipoEstoque codes used in titulo_bruto suffix.
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

function companyLabel(row) {
  return String(
    pickField(
      row,
      'razaoSocial',
      'razaosocial',
      'razao_social',
      'nomeEmpresa',
      'nomeempresa',
      'empresa',
      'company_name',
      'seller_company_name',
      'nomeFornecedor',
      'nomefornecedor',
      'fornecedor',
      'nomeLoja',
      'nomeloja',
      'loja',
      'nomeFilial',
      'nomefilial',
      'branch_name',
      'apelidoFilial',
      'apelidofilial'
    ) || ''
  ).trim();
}

const BRAZIL_STATE_UF = {
  acre: 'AC',
  alagoas: 'AL',
  amapa: 'AP',
  amazonas: 'AM',
  bahia: 'BA',
  ceara: 'CE',
  'distrito federal': 'DF',
  'espirito santo': 'ES',
  goias: 'GO',
  maranhao: 'MA',
  'mato grosso': 'MT',
  'mato grosso do sul': 'MS',
  'minas gerais': 'MG',
  para: 'PA',
  paraiba: 'PB',
  parana: 'PR',
  pernambuco: 'PE',
  piaui: 'PI',
  'rio de janeiro': 'RJ',
  'rio grande do norte': 'RN',
  'rio grande do sul': 'RS',
  rondonia: 'RO',
  roraima: 'RR',
  'santa catarina': 'SC',
  'sao paulo': 'SP',
  sergipe: 'SE',
  tocantins: 'TO',
};
const BRAZIL_UFS = new Set(Object.values(BRAZIL_STATE_UF));

function normalizeTextKey(value) {
  return String(value || '')
    .trim()
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '');
}

function normalizeUf(value) {
  const text = String(value || '').trim().toUpperCase();
  if (BRAZIL_UFS.has(text)) return text;
  const normalized = normalizeTextKey(value);
  if (BRAZIL_STATE_UF[normalized]) return BRAZIL_STATE_UF[normalized];
  const match = normalized
    .toUpperCase()
    .match(/\b(AC|AL|AP|AM|BA|CE|DF|ES|GO|MA|MT|MS|MG|PA|PB|PR|PE|PI|RJ|RN|RS|RO|RR|SC|SP|SE|TO)\b/);
  if (match) return match[1];
  for (const [state, uf] of Object.entries(BRAZIL_STATE_UF)) {
    if (normalized.includes(state)) return uf;
  }
  return '';
}

function sellerUf(row) {
  return normalizeUf(
    pickField(
      row,
      'uf',
      'UF',
      'estado',
      'Estado',
      'seller_uf',
      'seller_state',
      'state',
      'ufFilial',
      'uffilial',
      'estadoFilial',
      'estadofilial',
      'localizacao',
      'localização',
      'location',
      'cidade',
      'municipio',
      'município',
      'endereco',
      'endereço'
    ) || ''
  );
}

function normalizeCnpj(value) {
  const text = String(value || '');
  const match = text.match(/\d{2}\.?\d{3}\.?\d{3}\/?\d{4}-?\d{2}/);
  if (!match) return '';
  const digits = match[0].replace(/\D/g, '');
  return digits.length === 14 ? digits : '';
}

function cnpjFromRow(row) {
  return normalizeCnpj(
    pickField(
      row,
      'cnpj',
      'CNPJ',
      'seller_cnpj',
      'cnpjFilial',
      'cnpjfilial',
      'cnpjEmpresa',
      'cnpjempresa',
      'cnpjFornecedor',
      'cnpjfornecedor',
      'documento',
      'document',
      'tax_id'
    ) || ''
  );
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

function normalizeResultStatus(value, rows) {
  const raw = String(value || '').trim().toUpperCase();
  if (
    raw === 'FOUND_PRICE' ||
    raw === 'NO_PRICE' ||
    raw === 'NOT_FOUND' ||
    raw === 'BLOCKED' ||
    raw === 'TIMEOUT' ||
    raw === 'ERROR' ||
    raw === 'NOT_QUERIED'
  ) {
    return raw;
  }
  const lower = String(value || '').trim().toLowerCase();
  if (lower.includes('blocked') || lower.includes('captcha') || lower.includes('403')) return 'BLOCKED';
  if (lower.includes('timeout')) return 'TIMEOUT';
  if (lower.includes('error') || lower.includes('failed') || lower.includes('http_')) return 'ERROR';
  if (lower.includes('not_found') || lower.includes('not found') || lower.includes('no_results')) return 'NOT_FOUND';
  if (lower.includes('no_price') || lower.includes('sem_preco')) return 'NO_PRICE';
  const arr = Array.isArray(rows) ? rows : [];
  if (!arr.length) return 'NOT_FOUND';
  return hasValidPrice(rows) ? 'FOUND_PRICE' : 'NO_PRICE';
}

function normalizeSourceHealth(value, skuResult) {
  const raw = String(value || skuResult?.source_health || '').trim().toUpperCase();
  if (raw === 'OK' || raw === 'WORKING') return 'WORKING';
  if (raw === 'BLOCKED' || raw === 'TIMEOUT' || raw === 'ERROR' || raw === 'NOT_QUERIED') return raw;
  const result = normalizeResultStatus(skuResult?.sku_result || skuResult?.status || '', skuResult?.rows);
  if (result === 'BLOCKED' || result === 'TIMEOUT' || result === 'ERROR' || result === 'NOT_QUERIED') {
    return result;
  }
  return 'WORKING';
}

function hasValidPrice(rows) {
  return rowsForPricing(rows).some((row) => salePriceFromRow(row) !== null);
}

function sheetStatusForResult(resultStatus, hasPrice) {
  const raw = String(resultStatus || '').trim().toUpperCase();
  const lower = String(resultStatus || '').trim().toLowerCase();
  const status = normalizeResultStatus(resultStatus, []);
  const explicitNegative =
    raw === 'NO_PRICE' ||
    raw === 'NOT_FOUND' ||
    raw === 'BLOCKED' ||
    raw === 'TIMEOUT' ||
    raw === 'ERROR' ||
    raw === 'NOT_QUERIED' ||
    lower.includes('no_price') ||
    lower.includes('sem_preco') ||
    lower.includes('not_found') ||
    lower.includes('not found') ||
    lower.includes('blocked') ||
    lower.includes('captcha') ||
    lower.includes('timeout') ||
    lower.includes('error') ||
    lower.includes('failed') ||
    lower.includes('http_');
  if (status === 'FOUND_PRICE' || (hasPrice && !explicitNegative)) return '✅ Encontrado';
  if (status === 'NO_PRICE') return '⚠️ Sem preço';
  if (status === 'BLOCKED') return '🚫 Bloqueado';
  if (status === 'TIMEOUT' || status === 'ERROR') return '⚠️ Erro';
  return '❌ Não encontrado';
}

function availabilityForResult(resultStatus, stock) {
  const status = normalizeResultStatus(resultStatus, []);
  if (status === 'FOUND_PRICE') return toAvailabilityPt(stock);
  if (status === 'NO_PRICE') return 'sem_preco';
  if (status === 'BLOCKED') return 'bloqueado';
  if (status === 'TIMEOUT') return 'timeout';
  if (status === 'ERROR') return 'erro';
  if (status === 'NOT_QUERIED') return 'sem_resultados';
  return 'nao_encontrado';
}

function rawTitleForResult(resultStatus, fallback) {
  const status = normalizeResultStatus(resultStatus, []);
  const message = String(fallback || status || '').trim();
  if (status === 'BLOCKED') return 'BLOQUEADO: ' + (message || 'API Diversos bloqueado');
  if (status === 'TIMEOUT') return 'TIMEOUT: ' + (message || 'API Diversos timeout');
  if (status === 'ERROR') return 'ERRO: ' + (message || 'API Diversos erro');
  if (status === 'NO_PRICE') return 'SEM_PRECO: ' + (message || 'API Diversos sem preço');
  if (status === 'NOT_FOUND') return 'NOT_FOUND';
  return message || status;
}
