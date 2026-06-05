// cdp_router — API Diversos arm (inline POST to StokAPI). Runs for .analisar and .sku.

const DEFAULT_N8N_WEBHOOK_BASE = 'https://automacao.tktechnologies.com.br';

function readEnv(name) {
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
  return /^DEV\s*-/i.test(workflowName()) || /^dev$/i.test(readEnv('CDP_ENV'));
}
function devEnvName(name) {
  const map = {
    CDP_MUVSTOK_API_BASE: 'CDP_DEV_MUVSTOK_API_BASE',
    CDP_MUVSTOK_API_KEY: 'CDP_DEV_MUVSTOK_API_KEY',
    CDP_API_KEY: 'CDP_DEV_API_KEY',
    MUVSTOK_API_KEY: 'CDP_DEV_MUVSTOK_API_KEY',
    API_KEY: 'CDP_DEV_API_KEY',
    WEBHOOK_URL: 'CDP_DEV_WEBHOOK_URL',
    CDP_MUVSTOK_N8N_WEBHOOK_URL: 'CDP_DEV_MUVSTOK_N8N_WEBHOOK_URL',
    CDP_MUVSTOK_WEBHOOK_PATH: 'CDP_DEV_MUVSTOK_WEBHOOK_PATH',
  };
  return map[name] || '';
}
function envFor(name) {
  if (!isDevWorkflow()) return readEnv(name);
  const mapped = devEnvName(name);
  const value = mapped ? readEnv(mapped) : '';
  if (value) return value;
  if (name === 'WEBHOOK_URL') return readEnv('WEBHOOK_URL') || DEFAULT_N8N_WEBHOOK_BASE;
  if (name === 'CDP_MUVSTOK_WEBHOOK_PATH') return 'webhook/dev-muvstok-result';
  return '';
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
function encodeQueryParam(name, value) {
  return encodeURIComponent(name) + '=' + encodeURIComponent(String(value));
}
function looksLikeEmail(value) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(String(value || '').trim());
}

const dq = $input.first().json;
let chatId = '';
let emailFrom = '';
let notify = 'none';
let commandRoute = String(dq.command_route || dq.route || 'analisar');
let commandOrigin = String(dq.command_origin || dq.origem || '').trim().toLowerCase();
let replyChannel = String(dq.reply_channel || '').trim().toLowerCase();
try {
  const sd = $getWorkflowStaticData('global');
  const ctx = sd.cdp_sheet_requester || {};
  const notifyRaw = String(dq.notify || '').trim();
  chatId = String(dq.telegram_chat_id || dq.chat_id || '').trim();
  emailFrom = String(dq.email_from || '').trim();
  if (!emailFrom && looksLikeEmail(notifyRaw)) emailFrom = notifyRaw;
  const dataHasChannel = Boolean(
    replyChannel || commandOrigin === 'email' || commandOrigin === 'telegram' || emailFrom || chatId
  );
  if (!dataHasChannel && !replyChannel && ctx.reply_channel) {
    replyChannel = String(ctx.reply_channel).trim().toLowerCase();
  }
  if (!dataHasChannel && !commandOrigin && ctx.command_origin) {
    commandOrigin = String(ctx.command_origin).trim().toLowerCase();
  }
  if (!dataHasChannel && !emailFrom && ctx.email_from) emailFrom = String(ctx.email_from).trim();
  const inputIsEmail = commandOrigin === 'email' || replyChannel === 'email' || emailFrom;
  if (!inputIsEmail && !chatId && ctx.chat_id) chatId = String(ctx.chat_id).trim();
  if (ctx.command_route) commandRoute = String(ctx.command_route);
} catch (e) {}
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

const rawSkus = Array.isArray(dq.skus) ? dq.skus : [];
const rawSheetRows = Array.isArray(dq.sheet_rows) ? dq.sheet_rows : rawSkus;
if (!dq.valid_skus || dq.valid_skus < 1 || !rawSkus.length) {
  return [
    {
      json: {
        skip_stokapi: true,
        skip_muvstok: true,
        reason: 'no_skus',
        chat_id: notify === 'telegram' ? chatId : '',
        reply_email: notify === 'email' ? emailFrom : '',
        notify,
        reply_channel: replyChannel || notify,
        command_origin: commandOrigin || replyChannel || notify,
        command_route: commandRoute,
      },
    },
  ];
}

function skuKey(value) {
  return String(value || '')
    .trim()
    .toUpperCase()
    .replace(/[\s\-\.\\/]/g, '');
}

const skuRows = rawSkus
  .map((row) => {
    const sku = String(row.sku || row.SKU || row).trim().toUpperCase();
    return {
      sku,
      row_number: row.row_number ?? null,
      description: String(row.description || row.ITEM || '').trim(),
    };
  })
  .filter((r) => r.sku.length >= 3);
const dispatchedSkuKeys = new Set(skuRows.map((row) => skuKey(row.sku)));
const sheetRows = rawSheetRows
  .map((row) => {
    const sku = String(row.sku || row.SKU || row).trim().toUpperCase();
    return {
      sku,
      row_number: row.row_number ?? null,
      description: String(row.description || row.ITEM || '').trim(),
    };
  })
  .filter((row) => dispatchedSkuKeys.has(skuKey(row.sku)));

const batchGroupId =
  String(dq.batch_group_id || '').trim() ||
  'bg-' + Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 8);

let callbackUrl = envFor('CDP_MUVSTOK_N8N_WEBHOOK_URL');
if (!callbackUrl) {
  const base = trimTrailingSlashes(envFor('WEBHOOK_URL'));
  const rel = trimSlashes(envFor('CDP_MUVSTOK_WEBHOOK_PATH') || 'webhook/muvstok-result');
  if (base) callbackUrl = base + '/' + rel;
}
if (!callbackUrl && !isDevWorkflow()) {
  callbackUrl = 'https://automacao.tktechnologies.com.br/webhook/muvstok-result';
}

const deliveryMode = notify === 'none' ? 'legacy' : 'aggregate';
const queryParts = [
  encodeQueryParam('notify', notify),
  encodeQueryParam('reply_channel', replyChannel || notify),
  encodeQueryParam('command_origin', commandOrigin || replyChannel || notify),
  encodeQueryParam('batch_group_id', batchGroupId),
  encodeQueryParam('dual_run', 'stokapi'),
  encodeQueryParam('command_route', commandRoute),
  encodeQueryParam('delivery_mode', deliveryMode),
];
if (notify === 'telegram' && chatId) queryParts.push(encodeQueryParam('chat_id', chatId));
if (notify === 'email' && emailFrom) queryParts.push(encodeQueryParam('reply_email', emailFrom));
callbackUrl += (callbackUrl.includes('?') ? '&' : '?') + queryParts.join('&');

const apiBase = trimTrailingSlashes(
  envFor('CDP_MUVSTOK_API_BASE') ||
    (isDevWorkflow() ? '' : 'https://cdp-muv-api.bravecoast-b14d791e.eastus2.azurecontainerapps.io')
);
const apiKey =
  envFor('CDP_MUVSTOK_API_KEY') ||
  envFor('CDP_API_KEY') ||
  envFor('MUVSTOK_API_KEY') ||
  envFor('API_KEY');

const metadata = {
  source: 'cdp_router',
  pipeline: 'stokapi',
  command_route: commandRoute,
  command_origin: commandOrigin || replyChannel || notify,
  reply_channel: replyChannel || notify,
  notify,
  delivery_mode: notify === 'none' ? 'legacy' : 'aggregate',
  chat_id: notify === 'telegram' ? chatId : '',
  reply_email: notify === 'email' ? emailFrom : '',
  batch_index: 1,
  total_batches: 1,
  batch_group_id: batchGroupId,
  dispatched_at: dq.dispatched_at || new Date().toISOString(),
  unique_skus: skuRows.length,
  sheet_rows: sheetRows.length,
  duplicate_skus: Array.isArray(dq.duplicate_skus) ? dq.duplicate_skus : [],
};

return [
  {
    json: {
      skus: skuRows.map((r) => r.sku),
      sku_rows: sheetRows,
      callback_url: callbackUrl,
      api_jobs_url: apiBase + '/api/v1/muvstok/jobs',
      api_key: apiKey,
      metadata,
      idempotency_key: batchGroupId + '-stokapi-1',
      chat_id: notify === 'telegram' ? chatId : '',
      email_from: notify === 'email' ? emailFrom : '',
      notify,
      reply_channel: replyChannel || notify,
      command_origin: commandOrigin || replyChannel || notify,
      batch_group_id: batchGroupId,
      command_route: commandRoute,
    },
  },
];
