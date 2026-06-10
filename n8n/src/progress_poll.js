// cdp_progress — poll active dispatch runs and decide whether to notify.

function env(name, defaultVal) {
  try {
    if (typeof $env !== 'undefined' && $env && $env[name]) {
      return String($env[name]).trim() || defaultVal;
    }
  } catch (e) {}
  try {
    if (typeof process !== 'undefined' && process.env && process.env[name]) {
      return String(process.env[name]).trim() || defaultVal;
    }
  } catch (e) {}
  return defaultVal;
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
    CDP_PROGRESS_INTERVAL_MIN: 'CDP_DEV_PROGRESS_INTERVAL_MIN',
    CDP_PROGRESS_MIN_SKUS: 'CDP_DEV_PROGRESS_MIN_SKUS',
    CDP_PROGRESS_MIN_STEP_PCT: 'CDP_DEV_PROGRESS_MIN_STEP_PCT',
    CDP_PROGRESS_MAX_MESSAGES: 'CDP_DEV_PROGRESS_MAX_MESSAGES',
    CDP_SCRAPER_API_BASE: 'CDP_DEV_SCRAPER_API_BASE',
    MUVSTOK_SCRAPER_API_BASE: 'CDP_DEV_SCRAPER_API_BASE',
    CDP_MUVSTOK_API_BASE: 'CDP_DEV_MUVSTOK_API_BASE',
    CDP_API_KEY: 'CDP_DEV_API_KEY',
    MUVSTOK_API_KEY: 'CDP_DEV_API_KEY',
    API_KEY: 'CDP_DEV_API_KEY',
    CDP_MUVSTOK_API_KEY: 'CDP_DEV_MUVSTOK_API_KEY',
  };
  return map[name] || '';
}

function envFor(name, defaultVal) {
  if (!isDevWorkflow()) return env(name, defaultVal);
  const mapped = devEnvName(name);
  const value = mapped ? env(mapped, '') : '';
  return value || defaultVal;
}

function envInt(name, defaultVal) {
  const raw = envFor(name, '');
  if (!raw) return defaultVal;
  const n = parseInt(raw, 10);
  return Number.isFinite(n) ? n : defaultVal;
}

function trimTrailingSlashes(value) {
  let out = String(value || '').trim();
  while (out.endsWith('/')) out = out.slice(0, -1);
  return out;
}

const intervalMin = envInt('CDP_PROGRESS_INTERVAL_MIN', 10);
if (intervalMin <= 0) {
  return [{ json: { skip: true, reason: 'progress_disabled' } }];
}

const minSkus = envInt('CDP_PROGRESS_MIN_SKUS', 15);
const minStepPct = envInt('CDP_PROGRESS_MIN_STEP_PCT', 10);
const maxMessages = envInt('CDP_PROGRESS_MAX_MESSAGES', 6);

const scraperBase = trimTrailingSlashes(
  envFor('CDP_SCRAPER_API_BASE', envFor('MUVSTOK_SCRAPER_API_BASE', ''))
);
const stokapiBase = trimTrailingSlashes(
  envFor(
    'CDP_MUVSTOK_API_BASE',
    isDevWorkflow() ? '' : 'https://cdp-muv-api.bravecoast-b14d791e.eastus2.azurecontainerapps.io'
  )
);
const apiKey = envFor('CDP_API_KEY', envFor('MUVSTOK_API_KEY', envFor('API_KEY', '')));
const stokapiKey = envFor('CDP_MUVSTOK_API_KEY', apiKey);

const runsResp = $input.first().json;
const runs = Array.isArray(runsResp) ? runsResp : runsResp.runs || [];

if (!runs.length) {
  return [{ json: { skip: true, reason: 'no_active_runs' } }];
}

const out = [];
for (const run of runs) {
  if (!run || !run.chat_id) continue;
  if (run.progress_enabled === false) continue;
  if (Number(run.total_skus || 0) < minSkus) continue;
  if (Number(run.progress_message_count || 0) >= maxMessages) continue;

  const scraperIds = Array.isArray(run.scraper_job_ids) ? run.scraper_job_ids : [];
  const primaryScraper = scraperIds[0] || '';
  out.push({
    json: {
      skip: false,
      run_id: run.id,
      chat_id: run.chat_id,
      batch_group_id: run.batch_group_id,
      total_skus: run.total_skus,
      last_progress_notified_pct: Number(run.last_progress_pct || 0),
      min_step_pct: minStepPct,
      progress_message_count: Number(run.progress_message_count || 0),
      scraper_job_url: primaryScraper ? scraperBase + '/api/v1/jobs/' + primaryScraper : '',
      stokapi_job_url: run.stokapi_job_id
        ? stokapiBase + '/api/v1/muvstok/jobs/' + run.stokapi_job_id
        : '',
      scraper_api_key: apiKey,
      stokapi_api_key: stokapiKey,
      dispatch_runs_url: scraperBase + '/api/v1/dispatch-runs/' + run.id,
      dispatch_runs_api_key: apiKey,
    },
  });
}

if (!out.length) {
  return [{ json: { skip: true, reason: 'nothing_to_notify' } }];
}
return out;
