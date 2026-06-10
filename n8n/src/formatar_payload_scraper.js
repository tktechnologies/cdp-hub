// cdp_router — Scraper POST /api/v1/jobs (force_refresh=false → Redis/PostgreSQL 24h cache).

const DEFAULT_BATCH_SIZE = 100;
const MAX_BATCH_SIZE = 100;
const DEFAULT_SITES = [
  'gm',
  'ml',
  'vw',
  'eu',
];
const DEFAULT_SCRAPER_API_BASE =
  'https://cdp-scrapers-api-prod.bravecoast-b14d791e.eastus2.azurecontainerapps.io';
const DEFAULT_N8N_WEBHOOK_BASE = 'https://automacao.tktechnologies.com.br';
const data = $input.first().json;
const skus = Array.isArray(data.skus) ? data.skus : [];
const sheetRows = Array.isArray(data.sheet_rows) ? data.sheet_rows : skus;

function env(name) {
  try {
    if (typeof $env !== 'undefined' && $env && $env[name]) {
      return String($env[name]).trim();
    }
  } catch (e) {}
  try {
    if (typeof process !== 'undefined' && process.env && process.env[name]) {
      return String(process.env[name]).trim();
    }
  } catch (e) {}
  return '';
}
function workflowName() {
  try {
    if (typeof $workflow !== 'undefined' && $workflow && $workflow.name) {
      return String($workflow.name).trim();
    }
  } catch (e) {}
  return '';
}
function isDevWorkflow() {
  return /^DEV\s*-/i.test(workflowName());
}
function devEnvName(name) {
  const map = {
    CDP_SCRAPER_API_BASE: 'CDP_DEV_SCRAPER_API_BASE',
    MUVSTOK_SCRAPER_API_BASE: 'CDP_DEV_SCRAPER_API_BASE',
    CDP_API_KEY: 'CDP_DEV_API_KEY',
    MUVSTOK_API_KEY: 'CDP_DEV_API_KEY',
    API_KEY: 'CDP_DEV_API_KEY',
    CDP_SCRAPER_BATCH_SIZE: 'CDP_DEV_SCRAPER_BATCH_SIZE',
    CDP_SCRAPER_SITES: 'CDP_DEV_SCRAPER_SITES',
    WEBHOOK_URL: 'CDP_DEV_WEBHOOK_URL',
    CDP_N8N_WEBHOOK_URL: 'CDP_DEV_N8N_WEBHOOK_URL',
    CDP_N8N_WEBHOOK_PATH: 'CDP_DEV_N8N_WEBHOOK_PATH',
  };
  return map[name] || '';
}
function envFor(name) {
  if (!isDevWorkflow()) return env(name);
  const mapped = devEnvName(name);
  const value = mapped ? env(mapped) : '';
  if (value) return value;
  if (name === 'WEBHOOK_URL') return env('WEBHOOK_URL') || DEFAULT_N8N_WEBHOOK_BASE;
  if (name === 'CDP_N8N_WEBHOOK_PATH') return 'webhook/dev-scraper-result';
  return '';
}
function envList(name) {
  const raw = envFor(name);
  return raw ? raw.split(',').map((s) => s.trim()).filter(Boolean) : [];
}
function trimTrailingSlashes(value) {
  let out = String(value || '').trim();
  while (out.endsWith('/')) out = out.slice(0, -1);
  return out;
}
function trimSlashes(value) {
  let out = String(value || '').trim();
  while (out.startsWith('/')) out = out.slice(1);
  while (out.endsWith('/')) out = out.slice(0, -1);
  return out;
}
function readStaticRequester() {
  try {
    if (typeof $getWorkflowStaticData === 'function') {
      const sd = $getWorkflowStaticData('global');
      if (sd && sd.cdp_sheet_requester) return sd.cdp_sheet_requester;
    }
  } catch (e) {}
  return null;
}
function looksLikeEmail(value) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(String(value || '').trim());
}
function skuKey(value) {
  return String(value || '')
    .trim()
    .toUpperCase()
    .replace(/[\s\-\.\\/]/g, '');
}

const configuredSites = envList('CDP_SCRAPER_SITES');
const sites = configuredSites.length ? configuredSites : DEFAULT_SITES;
const commandRoute = String(data.command_route || 'analisar');
const scraperApiBase = trimTrailingSlashes(
  envFor('CDP_SCRAPER_API_BASE') ||
    envFor('MUVSTOK_SCRAPER_API_BASE') ||
    (isDevWorkflow() ? '' : DEFAULT_SCRAPER_API_BASE)
);
const apiKey = envFor('CDP_API_KEY') || envFor('MUVSTOK_API_KEY') || envFor('API_KEY');
const batchSizeRaw = Number(envFor('CDP_SCRAPER_BATCH_SIZE') || DEFAULT_BATCH_SIZE);
const BATCH_SIZE = Math.max(
  1,
  Math.min(MAX_BATCH_SIZE, Number.isFinite(batchSizeRaw) ? batchSizeRaw : DEFAULT_BATCH_SIZE)
);

const ctx = readStaticRequester();
let chatId = String(data.telegram_chat_id || data.chat_id || '').trim();
let emailFrom = String(data.email_from || '').trim();
const notifyRaw = String(data.notify || '').trim();
let commandOrigin = String(data.command_origin || data.origem || '').trim().toLowerCase();
let replyChannel = String(data.reply_channel || '').trim().toLowerCase();
if (!emailFrom && looksLikeEmail(notifyRaw)) emailFrom = notifyRaw;
const dataHasChannel = Boolean(
  replyChannel || commandOrigin === 'email' || commandOrigin === 'telegram' || emailFrom || chatId
);
if (ctx) {
  if (!dataHasChannel && !replyChannel && ctx.reply_channel) {
    replyChannel = String(ctx.reply_channel).trim().toLowerCase();
  }
  if (!dataHasChannel && !commandOrigin && ctx.command_origin) {
    commandOrigin = String(ctx.command_origin).trim().toLowerCase();
  }
  if (!dataHasChannel && !emailFrom && ctx.email_from) emailFrom = String(ctx.email_from).trim();
  const inputIsEmail = commandOrigin === 'email' || replyChannel === 'email' || emailFrom;
  if (!inputIsEmail && !chatId && ctx.chat_id) chatId = String(ctx.chat_id).trim();
}
let notify = 'none';
if (!replyChannel) {
  if (commandOrigin === 'email' || emailFrom) replyChannel = 'email';
  else if (commandOrigin === 'telegram' || chatId) replyChannel = 'telegram';
}
if (!commandOrigin && replyChannel) commandOrigin = replyChannel;
if (replyChannel === 'email') {
  notify = 'email';
  commandOrigin = 'email';
  chatId = '';
} else if (replyChannel === 'telegram') {
  notify = 'telegram';
  commandOrigin = 'telegram';
  emailFrom = '';
} else if (chatId) {
  notify = 'telegram';
  replyChannel = 'telegram';
  commandOrigin = commandOrigin || 'telegram';
} else if (emailFrom) {
  notify = 'email';
  replyChannel = 'email';
  commandOrigin = commandOrigin || 'email';
}

const batchGroupId =
  String(data.batch_group_id || '').trim() ||
  'bg-' + Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 8);
const adHoc = String(commandRoute || '').startsWith('sku');

let callbackUrl = envFor('CDP_N8N_WEBHOOK_URL');
if (!callbackUrl) {
  const base = trimTrailingSlashes(envFor('WEBHOOK_URL'));
  const rel = trimSlashes(envFor('CDP_N8N_WEBHOOK_PATH') || 'webhook/scraper-result');
  if (base) callbackUrl = base + '/' + rel;
}
if (!callbackUrl && !isDevWorkflow()) {
  callbackUrl = 'https://automacao.tktechnologies.com.br/webhook/scraper-result';
}

function encodeQueryParam(key, value) {
  return encodeURIComponent(key) + '=' + encodeURIComponent(String(value));
}
function buildQueryString(parts) {
  return parts.map(([k, v]) => encodeQueryParam(k, v)).join('&');
}
const deliveryMode = notify === 'none' ? 'legacy' : 'aggregate';
const queryParts = [
  ['notify', notify],
  ['reply_channel', replyChannel || notify],
  ['command_origin', commandOrigin || replyChannel || notify],
  ['batch_group_id', batchGroupId],
  ['dual_run', 'scraper'],
  ['command_route', commandRoute],
  ['delivery_mode', deliveryMode],
];
if (notify === 'telegram' && chatId) queryParts.push(['chat_id', chatId]);
if (notify === 'email' && emailFrom) queryParts.push(['reply_email', emailFrom]);
if (adHoc) queryParts.push(['ad_hoc', 'true']);
callbackUrl += (callbackUrl.includes('?') ? '&' : '?') + buildQueryString(queryParts);

const batches = [];
for (let i = 0; i < skus.length; i += BATCH_SIZE) {
  batches.push(skus.slice(i, i + BATCH_SIZE));
}
const totalBatches = batches.length;

return batches.map((batch, index) => {
  const batchSkuKeys = new Set(batch.map((it) => skuKey(it.sku)));
  const batchSheetRows = sheetRows.filter((it) => batchSkuKeys.has(skuKey(it.sku || it.SKU || it)));
  return {
    json: {
      callback_url: callbackUrl,
      items: batch.map((it) => ({
        sku: it.sku,
        brand: it.brand || '',
        description: it.description || '',
      })),
      sheet_rows: batchSheetRows.map((it) => ({
        sku: it.sku,
        row_number: it.row_number ?? null,
      })),
      sites,
      priority: 5,
      force_refresh: false,
      api_jobs_url: scraperApiBase + '/api/v1/jobs',
      api_key: apiKey,
      batch_group_id: batchGroupId,
      batch_index: index + 1,
      total_batches: totalBatches,
      batch_size: batch.length,
      sheet_row_count: batchSheetRows.length,
      ad_hoc: adHoc,
      notify,
      reply_channel: replyChannel || notify,
      command_origin: commandOrigin || replyChannel || notify,
      chat_id: notify === 'telegram' ? chatId : undefined,
      reply_email: notify === 'email' ? emailFrom : '',
      command_route: commandRoute,
      metadata: {
        source: 'cdp_router',
        pipeline: 'scraper',
        command_route: commandRoute,
        command_origin: commandOrigin || replyChannel || notify,
        reply_channel: replyChannel || notify,
        notify,
        delivery_mode: deliveryMode,
        chat_id: notify === 'telegram' ? chatId : '',
        reply_email: notify === 'email' ? emailFrom : '',
        batch_group_id: batchGroupId,
        batch_index: index + 1,
        total_batches: totalBatches,
        cache_policy: 'redis_24h',
        unique_skus: batch.length,
        sheet_rows: batchSheetRows.length,
      },
    },
  };
});
