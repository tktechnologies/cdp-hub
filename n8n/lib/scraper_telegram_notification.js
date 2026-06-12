// Telegram/email notification for cdp_scraper completion (injected into workflow JSON).
const ASSISTANT_NAME = 'Assistente CDP';
const WEBSCRAPERS_LABEL = 'WEBSCRAPERS';
const ESTOQUE_LABEL = 'ESTOQUE ONLINE';
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

function envFor(name) {
  if (!isDevWorkflow()) return env(name);
  const map = {
    CDP_RESULTADOS_SHEETS_URL: 'CDP_DEV_RESULTADOS_SHEETS_URL',
    NOTIFICATION_EMAIL_TO: 'CDP_DEV_NOTIFICATION_EMAIL_TO',
  };
  const mapped = map[name] || '';
  return mapped ? env(mapped) : '';
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
  const configured = envFor('CDP_RESULTADOS_SHEETS_URL');
  if (configured || isDevWorkflow()) return configured;
  return 'https://docs.google.com/spreadsheets/d/1ZBU2d3XVsngOYQH12yU7Mg9DcIzVet2dDmhMtZqHSOo/edit#gid=2127243308';
}

function escapeHtml(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

const wh = $('🔔 Webhook: Receber Resultados').first().json;
const payload = parseBody(wh.body);
const meta = typeof payload.job_metadata === 'object' && payload.job_metadata !== null ? payload.job_metadata : {};
const q = wh.query || {};
if (String(meta.delivery_mode || q.delivery_mode || '').trim().toLowerCase() === 'aggregate') {
  return [];
}
const results = payload.results || [];

let notify = String(meta.notify || q.notify || 'none').toLowerCase();
let replyChannel = String(
  meta.reply_channel || q.reply_channel || meta.command_origin || q.command_origin || ''
)
  .trim()
  .toLowerCase();
let chatId = String(meta.chat_id || q.chat_id || '').trim();
let replyEmail = String(meta.reply_email || q.reply_email || '').trim();
const fallbackEmail = envFor('NOTIFICATION_EMAIL_TO');
if (notify === 'email' && !replyEmail && fallbackEmail) replyEmail = fallbackEmail;
if (!replyChannel) {
  if (notify === 'email' || replyEmail) replyChannel = 'email';
  else if (notify === 'telegram' || chatId) replyChannel = 'telegram';
}
if (replyChannel === 'email') {
  notify = 'email';
  chatId = '';
} else if (replyChannel === 'telegram') {
  notify = 'telegram';
  replyEmail = '';
} else if (chatId) {
  notify = 'telegram';
  replyChannel = 'telegram';
} else if (replyEmail) {
  notify = 'email';
  replyChannel = 'email';
}

const origem = notify === 'telegram' ? 'telegram' : notify === 'email' ? 'email' : 'auto';

function numericPrice(value) {
  if (value === null || value === undefined || value === '') return null;
  const n = Number(value);
  return Number.isFinite(n) && n > 0 ? n : null;
}

function hasBestPrice(skuResult) {
  if (skuResult.has_valid_price === true || String(skuResult.sku_result || '').toUpperCase() === 'FOUND_PRICE') {
    return true;
  }
  const best = skuResult.best_price;
  if (best && best.exact_match !== false && numericPrice(best.price) !== null) return true;
  const sites = Array.isArray(skuResult.site_results) ? skuResult.site_results : [];
  return sites.some((siteResult) => {
    if (siteResult.has_valid_price === true || String(siteResult.sku_result || '').toUpperCase() === 'FOUND_PRICE') {
      return true;
    }
    const parts = Array.isArray(siteResult.results) ? siteResult.results : [];
    return parts.some((part) => !!(part && part.exact_match && numericPrice(part.price) !== null));
  });
}

function hasAnyResult(skuResult) {
  if (skuResult.has_any_exact_evidence === true || String(skuResult.sku_result || '').toUpperCase() === 'NO_PRICE') return true;
  const sites = Array.isArray(skuResult.site_results) ? skuResult.site_results : [];
  return sites.some((siteResult) => {
    const parts = Array.isArray(siteResult.results) ? siteResult.results : [];
    const status = String(siteResult.status || '').toLowerCase();
    return String(siteResult.sku_result || '').toUpperCase() === 'NO_PRICE'
      || status === 'no_price'
      || parts.some((part) => !!part.exact_match);
  });
}

const total = Number(payload.total_items || results.length || 0);
const resultCount = Number(payload.any_evidence_sku_count ?? results.filter(hasAnyResult).length);
const bestPriceCount = Number(payload.priced_sku_count ?? results.filter(hasBestPrice).length);
const noPriceCount = Number(payload.no_price_sku_count || 0);
const blockedCount = Number(payload.blocked_sku_count || 0);
const errorCount = Number(payload.error_sku_count || 0);
const pct = total ? ((bestPriceCount / total) * 100).toFixed(1) : '0.0';
const dur = Number(payload.duration_seconds ?? 0);
const notFound = Math.max(0, total - resultCount - blockedCount - errorCount);
const noComparableBestPrice = Math.max(0, resultCount - bestPriceCount);
const noPriceTotal = Math.max(noPriceCount, noComparableBestPrice);
const relUrl = reportUrl();

const headerLines = [
  '🤖 *' + ASSISTANT_NAME + '*',
  '',
  '✅ *' + WEBSCRAPERS_LABEL + ': busca concluída*',
  '',
  '📊 *' + bestPriceCount + '* de *' + total + '* com preço encontrado',
];
if (noPriceTotal > 0) headerLines.push('⚠️ Sem preço: *' + noPriceTotal + '*');
if (notFound > 0) headerLines.push('⚠️ Sem resultado: *' + notFound + '*');
if (blockedCount > 0) headerLines.push('🚫 Bloqueados: *' + blockedCount + '*');
if (errorCount > 0) headerLines.push('⚠️ Erros/timeouts: *' + errorCount + '*');

let telegramText = headerLines.join(NL);
if (relUrl) telegramText += NL + NL + '📎 Relatório: ' + relUrl;
if (telegramText.length > 4000) telegramText = telegramText.slice(0, 3990) + NL + '…';

const tone = errorCount > 0 || blockedCount > 0 ? '#b45309' : bestPriceCount > 0 ? '#047857' : '#334155';
const status = errorCount > 0 || blockedCount > 0 ? 'Concluído com avisos' : 'Busca em sites concluída';
const emailHtml =
  '<div style="margin:0;padding:0;background:#f6f8fb;font-family:Arial,Helvetica,sans-serif;color:#1f2937">' +
  '<div style="max-width:640px;margin:0 auto;padding:28px 18px">' +
  '<div style="background:#ffffff;border:1px solid #e5e7eb;border-radius:12px;overflow:hidden">' +
  '<div style="padding:22px 24px;border-bottom:1px solid #eef2f7">' +
  '<div style="font-size:12px;text-transform:uppercase;letter-spacing:0;color:#64748b;font-weight:700">' +
  escapeHtml(WEBSCRAPERS_LABEL) +
  '</div>' +
  '<h1 style="font-size:24px;line-height:1.25;margin:8px 0 0;color:#111827">' +
  escapeHtml(status) +
  '</h1>' +
  '</div>' +
  '<div style="padding:22px 24px">' +
  '<p style="font-size:15px;line-height:1.6;margin:0 0 18px">A busca nos sites públicos foi finalizada.</p>' +
  '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;margin:0 0 20px">' +
  '<tr>' +
  '<td style="padding:14px 16px;background:#f8fafc;border:1px solid #e5e7eb;border-radius:8px">' +
  '<div style="font-size:12px;color:#64748b;text-transform:uppercase;font-weight:700">Peças analisadas</div>' +
  '<div style="font-size:26px;font-weight:700;color:#111827;margin-top:4px">' +
  pecaLabel(total) +
  '</div>' +
  '</td>' +
  '<td width="12"></td>' +
  '<td style="padding:14px 16px;background:#f8fafc;border:1px solid #e5e7eb;border-radius:8px">' +
  '<div style="font-size:12px;color:#64748b;text-transform:uppercase;font-weight:700">Com preço</div>' +
  '<div style="font-size:26px;font-weight:700;color:' +
  tone +
  ';margin-top:4px">' +
  bestPriceCount +
  '</div>' +
  '</td>' +
  '</tr>' +
  '</table>' +
  '<div style="font-size:14px;line-height:1.7;color:#475569">' +
  '<strong>Taxa com preço:</strong> ' +
  pct +
  '%' +
  '<br><strong>Sem preço:</strong> ' +
  noPriceTotal +
  '<br><strong>Sem resultado:</strong> ' +
  notFound +
  '<br><strong>Bloqueados:</strong> ' +
  blockedCount +
  '<br><strong>Erros/timeouts:</strong> ' +
  errorCount +
  '<br><strong>Duração:</strong> ' +
  escapeHtml(durPt(dur)) +
  '</div>' +
  '<div style="background:#f8fafc;border:1px solid #e5e7eb;border-radius:8px;padding:12px 14px;margin:20px 0 0;font-size:13px;line-height:1.6;color:#475569">Este é o resultado de <strong>' +
  escapeHtml(WEBSCRAPERS_LABEL) +
  '</strong>. O resultado de <strong>' +
  escapeHtml(ESTOQUE_LABEL) +
  '</strong> chega em um e-mail separado quando a consulta de estoque terminar.</div>' +
  '<p style="margin:22px 0 0"><a href="' +
  escapeHtml(relUrl) +
  '" style="display:inline-block;background:#2563eb;color:#ffffff;text-decoration:none;border-radius:8px;padding:12px 18px;font-weight:700;font-size:14px">Abrir relatório</a></p>' +
  '</div>' +
  '</div>' +
  '<div style="font-size:12px;line-height:1.5;color:#94a3b8;text-align:center;padding:14px 0 0">Mensagem automática do Assistente CDP.</div>' +
  '</div>' +
  '</div>';
const emailSubject =
  ASSISTANT_NAME + ' - ' + WEBSCRAPERS_LABEL + ': busca concluída (' + bestPriceCount + '/' + total + ' com preço, ' + pct + '%)';

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
