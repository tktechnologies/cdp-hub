// cdp_router — Scraper POST /api/v1/jobs (force_refresh=false → Redis/PostgreSQL 24h cache).

const DEFAULT_BATCH_SIZE = 100;
const MAX_BATCH_SIZE = 100;
const DEFAULT_SITES = ['gm', 'ml', 'vw', 'eu', 'pecadireta'];
const data = $input.first().json;
const skus = Array.isArray(data.skus) ? data.skus : [];

function env(name) {
  try {
    if (typeof process !== 'undefined' && process.env && process.env[name]) {
      return String(process.env[name]).trim();
    }
  } catch (e) {}
  return '';
}
function envList(name) {
  const raw = env(name);
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

const configuredSites = envList('CDP_SCRAPER_SITES');
const sites = configuredSites.length ? configuredSites : DEFAULT_SITES;
const commandRoute = String(data.command_route || 'analisar');
const batchSizeRaw = Number(env('CDP_SCRAPER_BATCH_SIZE') || DEFAULT_BATCH_SIZE);
const BATCH_SIZE = Math.max(
  1,
  Math.min(MAX_BATCH_SIZE, Number.isFinite(batchSizeRaw) ? batchSizeRaw : DEFAULT_BATCH_SIZE)
);

const ctx = readStaticRequester();
let chatId = String(data.telegram_chat_id || data.chat_id || '').trim();
let emailFrom = String(data.email_from || '').trim();
if (ctx) {
  if (!chatId && ctx.chat_id) chatId = String(ctx.chat_id).trim();
  if (!emailFrom && ctx.email_from) emailFrom = String(ctx.email_from).trim();
}
const adHoc = !!(chatId || emailFrom);
let notify = 'none';
if (chatId) notify = 'telegram';
else if (emailFrom) notify = 'email';

const batchGroupId =
  String(data.batch_group_id || '').trim() ||
  'bg-' + Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 8);

let callbackUrl = env('CDP_N8N_WEBHOOK_URL');
if (!callbackUrl) {
  const base = trimTrailingSlashes(env('WEBHOOK_URL'));
  const rel = trimSlashes(env('CDP_N8N_WEBHOOK_PATH') || 'webhook/scraper-result');
  if (base) callbackUrl = base + '/' + rel;
}
if (!callbackUrl) callbackUrl = 'https://automacao.tktechnologies.com.br/webhook/scraper-result';

function encodeQueryParam(key, value) {
  return encodeURIComponent(key) + '=' + encodeURIComponent(String(value));
}
function buildQueryString(parts) {
  return parts.map(([k, v]) => encodeQueryParam(k, v)).join('&');
}
const queryParts = [
  ['notify', notify],
  ['batch_group_id', batchGroupId],
  ['dual_run', 'scraper'],
  ['command_route', commandRoute],
];
if (chatId) queryParts.push(['chat_id', chatId]);
if (emailFrom) queryParts.push(['reply_email', emailFrom]);
if (adHoc) queryParts.push(['ad_hoc', 'true']);
callbackUrl += (callbackUrl.includes('?') ? '&' : '?') + buildQueryString(queryParts);

const batches = [];
for (let i = 0; i < skus.length; i += BATCH_SIZE) {
  batches.push(skus.slice(i, i + BATCH_SIZE));
}
const totalBatches = batches.length;

return batches.map((batch, index) => ({
  json: {
    callback_url: callbackUrl,
    items: batch.map((it) => ({
      sku: it.sku,
      brand: it.brand || '',
      description: it.description || '',
    })),
    sites,
    priority: 5,
    force_refresh: false,
    batch_group_id: batchGroupId,
    batch_index: index + 1,
    total_batches: totalBatches,
    batch_size: batch.length,
    ad_hoc: adHoc,
    notify,
    chat_id: chatId || undefined,
    reply_email: emailFrom,
    command_route: commandRoute,
    metadata: {
      source: 'cdp_router',
      pipeline: 'scraper',
      command_route: commandRoute,
      batch_group_id: batchGroupId,
      batch_index: index + 1,
      total_batches: totalBatches,
      cache_policy: 'redis_24h',
    },
  },
}));
