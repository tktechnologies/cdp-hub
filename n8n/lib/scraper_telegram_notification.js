// Telegram/email notification for cdp_scraper completion (injected into workflow JSON).
const ASSISTANT_NAME = 'Assistente CDP';
const NL = '\n';

function parseBody(raw) {
  let p = raw;
  if (typeof p === 'string') {
    try {
      p = JSON.parse(p);
    } catch (e) {
      p = {};
    }
  }
  return p && typeof p === 'object' ? p : {};
}

function env(name) {
  try {
    if (typeof process !== 'undefined' && process.env && process.env[name]) {
      return String(process.env[name]).trim();
    }
  } catch (e) {}
  return '';
}

function durPt(seconds) {
  const s = Math.max(0, Math.round(Number(seconds) || 0));
  if (s >= 3600) {
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    return h + 'h ' + (m ? m + 'min' : '');
  }
  if (s >= 60) return Math.floor(s / 60) + ' min';
  return s + ' s';
}

function pecaLabel(n) {
  const x = Number(n) || 0;
  return x === 1 ? '1 peça' : x + ' peças';
}

function reportUrl() {
  return (
    env('CDP_RESULTADOS_SHEETS_URL') ||
    'https://docs.google.com/spreadsheets/d/1ZBU2d3XVsngOYQH12yU7Mg9DcIzVet2dDmhMtZqHSOo/edit#gid=533358674'
  );
}

const wh = $('🔔 Webhook: Receber Resultados').first().json;
const payload = parseBody(wh.body);
const meta = typeof payload.job_metadata === 'object' && payload.job_metadata !== null ? payload.job_metadata : {};
const q = wh.query || {};
const results = payload.results || [];

let notify = String(meta.notify || q.notify || 'none').toLowerCase();
const chatId = String(meta.chat_id || q.chat_id || '').trim();
let replyEmail = String(meta.reply_email || q.reply_email || '').trim();
const fallbackEmail = env('NOTIFICATION_EMAIL_TO');
if (notify === 'email' && !replyEmail && fallbackEmail) replyEmail = fallbackEmail;
if (chatId) notify = 'telegram';
else if (notify !== 'telegram' && notify !== 'email' && replyEmail) notify = 'email';

const origem = notify === 'telegram' ? 'telegram' : notify === 'email' ? 'email' : 'auto';

function numericPrice(value) {
  if (value === null || value === undefined || value === '') return null;
  const n = Number(value);
  return Number.isFinite(n) && n > 0 ? n : null;
}

function hasBestPrice(skuResult) {
  const best = skuResult.best_price;
  return !!(best && numericPrice(best.price) !== null);
}

function hasAnyResult(skuResult) {
  if (Number(skuResult.total_results || 0) > 0) return true;
  const sites = Array.isArray(skuResult.site_results) ? skuResult.site_results : [];
  return sites.some((siteResult) => {
    const parts = Array.isArray(siteResult.results) ? siteResult.results : [];
    const status = String(siteResult.status || '').toLowerCase();
    return parts.length > 0 || status === 'success' || status === 'no_price';
  });
}

const total = Number(payload.total_items || results.length || 0);
const resultCount = results.filter(hasAnyResult).length;
const bestPriceCount = results.filter(hasBestPrice).length;
const pct = total ? ((resultCount / total) * 100).toFixed(1) : '0.0';
const dur = Number(payload.duration_seconds ?? 0);
const notFound = Math.max(0, total - resultCount);
const noComparableBestPrice = Math.max(0, resultCount - bestPriceCount);
const relUrl = reportUrl();

const headerLines = [
  '🤖 *' + ASSISTANT_NAME + '*',
  '',
  '✅ *Busca em sites concluída*',
  '',
  '📊 *' + resultCount + '* de *' + total + '* com resultado',
];
if (bestPriceCount > 0) {
  headerLines.push('💰 Melhor preço comparável: *' + bestPriceCount + '*');
} else if (noComparableBestPrice > 0) {
  headerLines.push('💰 Melhor preço comparável: *0* (ver moedas/preços no relatório)');
}
if (notFound > 0) headerLines.push('⚠️ Sem resultado: *' + notFound + '*');

let telegramText = headerLines.join(NL);
if (relUrl) telegramText += NL + NL + '📎 Relatório: ' + relUrl;
if (telegramText.length > 4000) telegramText = telegramText.slice(0, 3990) + NL + '…';

const headerHtml =
  '<p><strong>' +
  ASSISTANT_NAME +
  '</strong> — busca em sites concluída.</p><ul>' +
  '<li>' +
  pecaLabel(total) +
  ' analisadas</li>' +
  '<li>' +
  resultCount +
  ' com resultado (' +
  pct +
  '%)</li>' +
  '<li>Melhor preço comparável: ' +
  bestPriceCount +
  '</li>' +
  '<li>Sem resultado: ' +
  notFound +
  '</li>' +
  '<li>Duração: ' +
  durPt(dur) +
  '</li></ul>' +
  '<p><a href="' +
  relUrl +
  '">Abrir relatório de resultados</a></p>';

const emailHtml =
  '<p>Olá,</p>' + headerHtml + '<p style="color:#718096;font-size:12px">— ' + ASSISTANT_NAME + '</p>';
const emailSubject = ASSISTANT_NAME + ' — ' + resultCount + '/' + total + ' peças com resultado (' + pct + '%)';

if (notify === 'telegram' && chatId) {
  return [
    {
      json: {
        notify: 'telegram',
        origem,
        telegram_chat_id: chatId,
        telegram_text: telegramText,
        email_to: '',
        email_subject: emailSubject,
        email_html: '',
        _total_items: total,
      },
    },
  ];
}

if (notify === 'email' && replyEmail) {
  return [
    {
      json: {
        notify: 'email',
        origem,
        telegram_chat_id: '',
        telegram_text: '',
        email_to: replyEmail,
        email_subject: emailSubject,
        email_html: emailHtml,
        _total_items: total,
      },
    },
  ];
}

return [
  {
    json: {
      notify: 'none',
      origem,
      telegram_chat_id: '',
      telegram_text: '',
      email_to: '',
      email_subject: '',
      email_html: '',
      _no_delivery: true,
      _total_items: total,
    },
  },
];
