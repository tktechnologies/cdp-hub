// cdp_router — format combined scraper + StokAPI progress for Telegram.

function num(v, fallback) {
  const n = Number(v);
  return Number.isFinite(n) ? n : fallback;
}

function statusLabel(status) {
  const s = String(status || '').toLowerCase();
  if (s === 'completed' || s === 'succeeded') return 'concluído';
  if (s === 'partial' || s === 'partially_succeeded') return 'parcial';
  if (s === 'failed') return 'falhou';
  if (s === 'running' || s === 'processing') return 'em execução';
  if (s === 'pending' || s === 'queued') return 'na fila';
  return s || 'desconhecido';
}

function formatDuration(seconds) {
  const sec = Math.max(0, Math.round(num(seconds, 0)));
  if (sec < 60) return '~' + sec + ' s';
  const mins = Math.ceil(sec / 60);
  return mins === 1 ? '~1 minuto' : '~' + mins + ' minutos';
}

function formatClock(iso) {
  if (!iso) return '—';
  try {
    const d = new Date(iso);
    return d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
  } catch (e) {
    return '—';
  }
}

const prep = $('📊 Status: preparar').first().json;
if (prep.skip_poll) {
  return [{ json: { chat_id: prep.chat_id, msg_telegram: prep.msg_telegram } }];
}

let scraper = {};
let stokapi = {};
try {
  scraper = $('📊 GET Scraper Job').first().json;
} catch (e) {}
try {
  stokapi = $('📊 GET StokAPI Job').first().json;
} catch (e) {}

const total = num(prep.total_skus, num(scraper.total_items, num(stokapi.submitted_sku_count, 0)));
const scraperProcessed = num(
  scraper.items_processed,
  num(scraper.items_succeeded, 0) + num(scraper.items_failed, 0)
);
const scraperPct = num(scraper.progress_pct, total > 0 ? (scraperProcessed / total) * 100 : 0);
const stokProcessed = num(
  stokapi.processed_sku_count,
  num(stokapi.succeeded_sku_count, 0) + num(stokapi.failed_sku_count, 0)
);
const stokPct = num(stokapi.progress_pct, total > 0 ? (stokProcessed / total) * 100 : 0);

const dispatchedAt = prep.dispatched_at || scraper.started_at;
const elapsedSec = dispatchedAt
  ? Math.max(0, Math.floor((Date.now() - new Date(dispatchedAt).getTime()) / 1000))
  : 0;

const scraperEta = scraper.estimated_seconds_remaining;
const stokEta = stokapi.estimated_seconds_remaining;
const etaSec =
  num(scraperEta, null) != null && scraperEta > 0
    ? scraperEta
    : num(stokEta, null) != null && stokEta > 0
      ? stokEta
      : Math.max(0, num(prep.estimated_seconds, 0) - elapsedSec);

const lines = [
  '🤖 *Assistente CDP* — andamento',
  '',
  '📦 *Sites (scraper):* ' +
    scraperProcessed +
    '/' +
    (total || '?') +
    ' peças (~' +
    Math.round(scraperPct) +
    '%) — ' +
    statusLabel(scraper.status),
];

if (etaSec > 0 && String(scraper.status || '').toLowerCase() === 'running') {
  lines.push('⏱️ ' + formatDuration(etaSec) + ' restantes (estimativa)');
}
lines.push(
  '🕐 Início: ' + formatClock(dispatchedAt) + ' · Já decorrido: ' + formatDuration(elapsedSec)
);
lines.push('');
lines.push(
  '📦 *Estoque:* ' +
    statusLabel(stokapi.status) +
    ' (' +
    stokProcessed +
    '/' +
    (total || '?') +
    ' com dados, ~' +
    Math.round(stokPct) +
    '%)'
);

const scraperTerminal = ['completed', 'partial', 'failed'].includes(
  String(scraper.status || '').toLowerCase()
);
const stokTerminal = ['succeeded', 'partially_succeeded', 'failed'].includes(
  String(stokapi.status || '').toLowerCase()
);

try {
  if (typeof $getWorkflowStaticData === 'function') {
    const sd = $getWorkflowStaticData('global');
    if (sd.cdp_active_run) {
      sd.cdp_active_run.scraper_completed = scraperTerminal;
      sd.cdp_active_run.stokapi_completed = stokTerminal;
      if (scraperTerminal && stokTerminal) {
        delete sd.cdp_active_run;
      }
    }
  }
} catch (e) {}

return [{ json: { chat_id: prep.chat_id, msg_telegram: lines.join('\n') } }];
