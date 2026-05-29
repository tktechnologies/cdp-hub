// cdp_router — .status / .andamento: resolve active run and API poll targets.

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

function trimTrailingSlashes(value) {
  let out = String(value || '').trim();
  while (out.endsWith('/')) out = out.slice(0, -1);
  return out;
}

const router = $input.first().json;
const chatId = String(router.chat_id || router.notify || '').trim();

let run = null;
try {
  if (typeof $getWorkflowStaticData === 'function') {
    run = $getWorkflowStaticData('global').cdp_active_run || null;
  }
} catch (e) {}

if (!run || !run.batch_group_id) {
  try {
    const apiRun = $('📊 GET dispatch run (chat)').first().json;
    if (apiRun && apiRun.batch_group_id) {
      run = {
        batch_group_id: apiRun.batch_group_id,
        scraper_job_ids: apiRun.scraper_job_ids || [],
        stokapi_job_id: apiRun.stokapi_job_id || '',
        total_skus: Number(apiRun.total_skus || 0),
        dispatched_at: apiRun.dispatched_at,
        estimated_seconds: Number(apiRun.estimated_seconds || 0),
        chat_id: apiRun.chat_id,
      };
    }
  } catch (e) {}
}

const TTL_HOURS = 24;
if (run && run.dispatched_at) {
  const ageMs = Date.now() - new Date(run.dispatched_at).getTime();
  if (ageMs > TTL_HOURS * 60 * 60 * 1000) {
    run = null;
  }
}

if (!run || !run.batch_group_id) {
  return [
    {
      json: {
        skip_poll: true,
        chat_id: chatId,
        msg_telegram:
          '🤖 *Assistente CDP*\n\nNenhuma consulta em andamento.\nUse `.analisar` ou `.sku` para iniciar.',
      },
    },
  ];
}

if (chatId && run.chat_id && chatId !== String(run.chat_id).trim()) {
  return [
    {
      json: {
        skip_poll: true,
        chat_id: chatId,
        msg_telegram:
          '🤖 *Assistente CDP*\n\nNão há consulta ativa para este chat.\nUse `.analisar` ou `.sku` para iniciar.',
      },
    },
  ];
}

const scraperBase = trimTrailingSlashes(
  env('CDP_SCRAPER_API_BASE') || env('MUVSTOK_SCRAPER_API_BASE') || DEFAULT_SCRAPER_API_BASE
);
const stokapiBase = trimTrailingSlashes(
  env('CDP_MUVSTOK_API_BASE') ||
    'https://cdp-muv-api.bravecoast-b14d791e.eastus2.azurecontainerapps.io'
);
const apiKey = env('CDP_API_KEY') || env('MUVSTOK_API_KEY') || env('API_KEY');
const stokapiKey = env('CDP_MUVSTOK_API_KEY') || apiKey;

const scraperJobIds = Array.isArray(run.scraper_job_ids) ? run.scraper_job_ids : [];
const primaryScraperJobId = scraperJobIds[0] || '';

return [
  {
    json: {
      skip_poll: false,
      chat_id: chatId || run.chat_id,
      batch_group_id: run.batch_group_id,
      total_skus: Number(run.total_skus || 0),
      dispatched_at: run.dispatched_at,
      estimated_seconds: Number(run.estimated_seconds || 0),
      scraper_job_ids: scraperJobIds,
      stokapi_job_id: String(run.stokapi_job_id || ''),
      scraper_job_url: primaryScraperJobId
        ? scraperBase + '/api/v1/jobs/' + primaryScraperJobId
        : '',
      stokapi_job_url: run.stokapi_job_id
        ? stokapiBase + '/api/v1/muvstok/jobs/' + run.stokapi_job_id
        : '',
      scraper_api_key: apiKey,
      stokapi_api_key: stokapiKey,
    },
  },
];
