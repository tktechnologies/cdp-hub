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
function workflowName() {
  try {
    if (typeof $workflow !== 'undefined' && $workflow && $workflow.name) {
      return String($workflow.name).trim();
    }
  } catch (e) {}
  return '';
}
function workflowTarget() {
  const name = workflowName();
  if (/^DEV\s*-/i.test(name)) return 'dev';
  if (/^STOKAI\s*-/i.test(name)) return 'stokai';
  return 'prod';
}
function isDevWorkflow() {
  return workflowTarget() === 'dev';
}
function targetEnvName(name, target) {
  const prefix = target === 'stokai' ? 'CDP_STOKAI' : 'CDP_DEV';
  const map = {
    CDP_SCRAPER_API_BASE: `${prefix}_SCRAPER_API_BASE`,
    MUVSTOK_SCRAPER_API_BASE: `${prefix}_SCRAPER_API_BASE`,
    CDP_MUVSTOK_API_BASE: `${prefix}_MUVSTOK_API_BASE`,
    CDP_API_KEY: `${prefix}_API_KEY`,
    MUVSTOK_API_KEY: `${prefix}_API_KEY`,
    API_KEY: `${prefix}_API_KEY`,
    CDP_MUVSTOK_API_KEY: `${prefix}_MUVSTOK_API_KEY`,
  };
  return map[name] || '';
}
function envFor(name) {
  const target = workflowTarget();
  if (target === 'prod') return env(name);
  const mapped = targetEnvName(name, target);
  return mapped ? env(mapped) : '';
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
  envFor('CDP_SCRAPER_API_BASE') ||
    envFor('MUVSTOK_SCRAPER_API_BASE') ||
    (workflowTarget() === 'prod' ? DEFAULT_SCRAPER_API_BASE : '')
);
const stokapiBase = trimTrailingSlashes(
  envFor('CDP_MUVSTOK_API_BASE') ||
    (workflowTarget() === 'prod' ? 'https://cdp-muv-api.bravecoast-b14d791e.eastus2.azurecontainerapps.io' : '')
);
const apiKey = envFor('CDP_API_KEY') || envFor('MUVSTOK_API_KEY') || envFor('API_KEY');
const stokapiKey = envFor('CDP_MUVSTOK_API_KEY') || apiKey;

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
