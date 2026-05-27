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

function hasBestPrice(skuResult) {
  const best = skuResult.best_price;
  return !!(best && best.price != null && Number(best.price) > 0);
}

const total = Number(payload.total_items || results.length || 0);
const found = results.filter(hasBestPrice).length;
const pct = total ? ((found / total) * 100).toFixed(1) : '0.0';
const dur = Number(payload.duration_seconds ?? 0);
const notFound = Math.max(0, total - found);
const relUrl = reportUrl();

const headerLines = [
  '🤖 *' + ASSISTANT_NAME + '*',
  '',
  '✅ *Busca em sites concluída*',
  '',
  '📊 *' + found + '* de *' + total + '* com melhor preço',
];
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
  found +
  ' com melhor preço (' +
  pct +
  '%)</li>' +
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
const emailSubject = ASSISTANT_NAME + ' — ' + found + '/' + total + ' peças com preço (' + pct + '%)';

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
