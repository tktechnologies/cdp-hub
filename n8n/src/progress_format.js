// cdp_progress — format proactive update and PATCH dispatch run state.

function num(v, fallback) {
  const n = Number(v);
  return Number.isFinite(n) ? n : fallback;
}

const ctx = $('📊 Progress: preparar runs').item.json;
let scraper = {};
let stokapi = {};
try {
  scraper = $('📊 Progress: GET Scraper').first().json;
} catch (e) {}
try {
  stokapi = $('📊 Progress: GET StokAPI').first().json;
} catch (e) {}

const total = num(ctx.total_skus, num(scraper.total_items, 0));
const processed = num(
  scraper.items_processed,
  num(scraper.items_succeeded, 0) + num(scraper.items_failed, 0)
);
const pct = total > 0 ? Math.round((processed / total) * 100) : 0;
const lastPct = num(ctx.last_progress_notified_pct, 0);
const minStep = num(ctx.min_step_pct, 10);

const scraperTerminal = ['completed', 'partial', 'failed'].includes(
  String(scraper.status || '').toLowerCase()
);
const stokTerminal = ['succeeded', 'partially_succeeded', 'failed'].includes(
  String(stokapi.status || '').toLowerCase()
);

if (scraperTerminal && stokTerminal) {
  return [
    {
      json: {
        skip_notify: true,
        run_id: ctx.run_id,
        chat_id: ctx.chat_id,
        patch_url: ctx.dispatch_runs_url,
        patch_api_key: ctx.dispatch_runs_api_key,
        patch_body: {
          last_progress_pct: 100,
          progress_message_count: num(ctx.progress_message_count, 0),
          scraper_status: String(scraper.status || 'completed'),
          stokapi_status: String(stokapi.status || 'succeeded'),
          completed_at: new Date().toISOString(),
        },
      },
    },
  ];
}

if (pct - lastPct < minStep && String(scraper.status || '').toLowerCase() === 'running') {
  return [{ json: { skip_notify: true, reason: 'step_too_small' } }];
}

const eta = num(scraper.estimated_seconds_remaining, 0);
const etaLine = eta > 0 ? ' · ~' + Math.ceil(eta / 60) + ' min restantes' : '';

const msg =
  '🤖 *Atualização* — sites: ' +
  processed +
  '/' +
  total +
  ' peças (' +
  pct +
  '%)' +
  etaLine;

return [
  {
    json: {
      skip_notify: false,
      chat_id: ctx.chat_id,
      msg_telegram: msg,
      run_id: ctx.run_id,
      patch_url: ctx.dispatch_runs_url,
      patch_api_key: ctx.dispatch_runs_api_key,
      patch_body: {
        last_progress_pct: pct,
        progress_message_count: num(ctx.progress_message_count, 0) + 1,
        scraper_status: String(scraper.status || 'running'),
        stokapi_status: String(stokapi.status || 'processing'),
      },
    },
  },
];
