// cdp_router — API Diversos arm (inline POST to StokAPI). Runs for .analisar and .sku.

function readEnv(name) {
  try {
    if (typeof process !== 'undefined' && process.env && process.env[name]) {
      return String(process.env[name]).trim();
    }
  } catch (e) {}
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

const dq = $input.first().json;
let chatId = '';
let emailFrom = '';
let notify = 'none';
let commandRoute = String(dq.command_route || dq.route || 'analisar');
try {
  const sd = $getWorkflowStaticData('global');
  const ctx = sd.cdp_sheet_requester || {};
  chatId = String(ctx.chat_id || dq.telegram_chat_id || dq.chat_id || '').trim();
  emailFrom = String(ctx.email_from || dq.email_from || '').trim();
  notify = String(ctx.notify || (chatId ? 'telegram' : emailFrom ? 'email' : 'none'));
  if (ctx.command_route) commandRoute = String(ctx.command_route);
} catch (e) {}

const rawSkus = Array.isArray(dq.skus) ? dq.skus : [];
if (!dq.valid_skus || dq.valid_skus < 1 || !rawSkus.length) {
  return [
    {
      json: {
        skip_stokapi: true,
        skip_muvstok: true,
        reason: 'no_skus',
        chat_id: chatId,
        command_route: commandRoute,
      },
    },
  ];
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

const batchGroupId =
  String(dq.batch_group_id || '').trim() ||
  'bg-' + Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 8);

let callbackUrl = readEnv('CDP_MUVSTOK_N8N_WEBHOOK_URL');
if (!callbackUrl) {
  const base = trimTrailingSlashes(readEnv('WEBHOOK_URL'));
  const rel = trimSlashes(readEnv('CDP_MUVSTOK_WEBHOOK_PATH') || 'webhook/muvstok-result');
  if (base) callbackUrl = base + '/' + rel;
}
if (!callbackUrl) callbackUrl = 'https://automacao.tktechnologies.com.br/webhook/muvstok-result';

const queryParts = [
  encodeQueryParam('notify', notify),
  encodeQueryParam('batch_group_id', batchGroupId),
  encodeQueryParam('dual_run', 'stokapi'),
  encodeQueryParam('command_route', commandRoute),
];
if (chatId) queryParts.push(encodeQueryParam('chat_id', chatId));
if (emailFrom) queryParts.push(encodeQueryParam('reply_email', emailFrom));
callbackUrl += (callbackUrl.includes('?') ? '&' : '?') + queryParts.join('&');

const apiBase = trimTrailingSlashes(
  readEnv('CDP_MUVSTOK_API_BASE') ||
    'https://cdp-muv-api.bravecoast-b14d791e.eastus2.azurecontainerapps.io'
);

const metadata = {
  source: 'cdp_router',
  pipeline: 'stokapi',
  command_route: commandRoute,
  batch_index: 1,
  total_batches: 1,
  batch_group_id: batchGroupId,
  dispatched_at: dq.dispatched_at || new Date().toISOString(),
};

return [
  {
    json: {
      skus: skuRows.map((r) => r.sku),
      sku_rows: skuRows,
      callback_url: callbackUrl,
      api_jobs_url: apiBase + '/api/v1/muvstok/jobs',
      metadata,
      idempotency_key: batchGroupId + '-stokapi-1',
      chat_id: chatId,
      email_from: emailFrom,
      notify,
      batch_group_id: batchGroupId,
      command_route: commandRoute,
    },
  },
];
