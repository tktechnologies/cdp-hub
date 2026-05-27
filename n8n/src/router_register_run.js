// cdp_router — persist active dual-pipeline run (staticData + dispatch_runs API).

function env(name) {
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

const scraperResponses = $('🚀 POST → Scraper API (/jobs)').all();
const scraperJobIds = scraperResponses
  .map((item) => String(item.json.job_id || '').trim())
  .filter(Boolean);

let stokapiJobId = '';
try {
  const stokResp = $('🚀 POST API Diversos').first().json;
  stokapiJobId = String(stokResp.job_id || stokResp.id || '').trim();
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
const commandRoute = String(dispatch.command_route || 'analisar');
const totalSkus = Number(dispatch.valid_skus || 0);
const estimatedSeconds = Number(confirmacao.mins || 0) * 60;

const activeRun = {
  batch_group_id: batchGroupId,
  scraper_job_ids: scraperJobIds,
  stokapi_job_id: stokapiJobId,
  total_skus: totalSkus,
  dispatched_at: new Date().toISOString(),
  estimated_seconds: estimatedSeconds,
  chat_id: chatId,
  command_route: commandRoute,
  scraper_completed: false,
  stokapi_completed: false,
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
  env('CDP_SCRAPER_API_BASE') || env('MUVSTOK_SCRAPER_API_BASE') || ''
);
const apiKey = env('CDP_API_KEY') || env('MUVSTOK_API_KEY') || env('API_KEY');

return [
  {
    json: {
      registered: true,
      ...activeRun,
      dispatch_runs_url: apiBase ? apiBase + '/api/v1/dispatch-runs' : '',
      dispatch_runs_api_key: apiKey,
    },
  },
];
