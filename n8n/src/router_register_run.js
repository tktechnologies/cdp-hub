// cdp_router — persist active dual-pipeline run (staticData + dispatch_runs API).

const DEFAULT_SCRAPER_API_BASE =
  'https://cdp-scrapers-api-prod.bravecoast-b14d791e.eastus2.azurecontainerapps.io';

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
      return String($workflow.name);
    }
  } catch (e) {}
  return '';
}

function isDevWorkflow() {
  return workflowName().trim().toLowerCase().startsWith('dev -') || env('CDP_ENV').toLowerCase() === 'dev';
}

function devEnvName(name) {
  return {
    CDP_SCRAPER_API_BASE: 'CDP_DEV_SCRAPER_API_BASE',
    MUVSTOK_SCRAPER_API_BASE: 'CDP_DEV_SCRAPER_API_BASE',
    CDP_API_KEY: 'CDP_DEV_API_KEY',
    MUVSTOK_API_KEY: 'CDP_DEV_API_KEY',
    API_KEY: 'CDP_DEV_API_KEY',
  }[name] || '';
}

function envFor(name, defaultVal = '') {
  if (!isDevWorkflow()) return env(name) || defaultVal;
  const mapped = devEnvName(name);
  if (mapped) return env(mapped) || defaultVal;
  return env(name) || defaultVal;
}

function trimTrailingSlashes(value) {
  let out = String(value || '').trim();
  while (out.endsWith('/')) out = out.slice(0, -1);
  return out;
}

let scraperJobIds = [];
try {
  const scraperResponses = $('🚀 POST → Scraper API (/jobs)').all();
  scraperJobIds = scraperResponses
    .map((item) => String(item.json.job_id || item.json.body?.job_id || '').trim())
    .filter(Boolean);
} catch (e) {}

let stokapiJobId = '';
try {
  const stokResp = $('🚀 POST API Diversos').first().json;
  stokapiJobId = String(stokResp.job_id || stokResp.id || stokResp.body?.job_id || '').trim();
} catch (e) {}

let dispatch = {};
try {
  dispatch = $('🎲 Limitar SKUs').first().json;
} catch (e) {}

let confirmacao = {};
try {
  confirmacao = $('📋 Formatar Confirmação (Planilha)').first().json;
} catch (e) {}

const batchGroupId = String(dispatch.batch_group_id || '').trim();
const chatId = String(confirmacao.chat_id || dispatch.chat_id || dispatch.telegram_chat_id || '').trim();
const replyChannel = String(confirmacao.reply_channel || dispatch.reply_channel || '').trim().toLowerCase();
const replyEmail = String(confirmacao.email_from || dispatch.reply_email || dispatch.email_from || '').trim();
const commandOrigin = String(
  confirmacao.command_origin || dispatch.command_origin || replyChannel || ''
).trim().toLowerCase();
const commandRoute = String(dispatch.command_route || 'analisar');
const totalSkus = Number(dispatch.valid_skus || dispatch.total_skus || 0);
const estimatedSeconds = Number(confirmacao.mins || 0) * 60;
const dispatchedAt = String(dispatch.dispatched_at || new Date().toISOString());
const sheetRows = Array.isArray(dispatch.sheet_rows) ? dispatch.sheet_rows : [];
const sheetRowNumbers = [
  ...new Set(
    sheetRows
      .map((row) => Number(row.row_number))
      .filter((n) => Number.isFinite(n) && n > 0)
  ),
];
const hasRecipient =
  (replyChannel === 'telegram' && chatId) || (replyChannel === 'email' && replyEmail) || chatId || replyEmail;
const deliveryMode = hasRecipient ? 'aggregate' : 'legacy';
const progressEnabled = deliveryMode !== 'aggregate';

let previousRun = null;
try {
  if (typeof $getWorkflowStaticData === 'function') {
    previousRun = $getWorkflowStaticData('global').cdp_active_run || null;
  }
} catch (e) {}

if (previousRun && String(previousRun.batch_group_id || '') === batchGroupId) {
  const mergedScraperIds = [
    ...(Array.isArray(previousRun.scraper_job_ids) ? previousRun.scraper_job_ids : []),
    ...scraperJobIds,
  ]
    .map((id) => String(id || '').trim())
    .filter(Boolean);
  scraperJobIds = [...new Set(mergedScraperIds)];
  stokapiJobId = stokapiJobId || String(previousRun.stokapi_job_id || '').trim();
}

if (!scraperJobIds.length && !stokapiJobId) {
  return [];
}

const activeRun = {
  batch_group_id: batchGroupId,
  scraper_job_ids: scraperJobIds,
  stokapi_job_id: stokapiJobId,
  total_skus: totalSkus,
  dispatched_at: previousRun?.batch_group_id === batchGroupId ? previousRun.dispatched_at || dispatchedAt : dispatchedAt,
  estimated_seconds: estimatedSeconds,
  chat_id: chatId,
  reply_channel: replyChannel || (replyEmail ? 'email' : chatId ? 'telegram' : ''),
  reply_email: replyEmail,
  command_origin: commandOrigin,
  command_route: commandRoute,
  progress_enabled: progressEnabled,
  delivery_mode: deliveryMode,
  sheet_row_numbers: sheetRowNumbers,
  scraper_completed: scraperJobIds.length < 1,
  stokapi_completed: !stokapiJobId,
  last_progress_notified_pct: 0,
  progress_message_count: 0,
};

try {
  if (typeof $getWorkflowStaticData === 'function') {
    const sd = $getWorkflowStaticData('global');
    sd.cdp_active_run = activeRun;
  }
} catch (e) {}

const apiBase = trimTrailingSlashes(
  envFor('CDP_SCRAPER_API_BASE') ||
    envFor('MUVSTOK_SCRAPER_API_BASE') ||
    (isDevWorkflow() ? '' : DEFAULT_SCRAPER_API_BASE)
);
const apiKey = envFor('CDP_API_KEY') || envFor('MUVSTOK_API_KEY') || envFor('API_KEY');

return [
  {
    json: {
      registered: true,
      ...activeRun,
      dispatch_runs_url: apiBase ? apiBase + '/api/v1/dispatch-runs' : '',
      dispatch_runs_api_key: apiKey,
      reply_channel: replyChannel || (replyEmail ? 'email' : chatId ? 'telegram' : ''),
      reply_email: replyEmail,
      command_origin: commandOrigin,
      progress_enabled: progressEnabled,
      delivery_mode: deliveryMode,
      sheet_row_numbers: sheetRowNumbers,
    },
  },
];
