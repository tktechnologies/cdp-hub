// User-facing same-channel notification for API Diversos completion (injected into cdp_stokapi).
const ASSISTANT_NAME = 'Assistente CDP';
const WEBSCRAPERS_LABEL = 'WEBSCRAPERS';
const ESTOQUE_LABEL = 'ESTOQUE ONLINE';

let j = {};
try {
  if (typeof $getWorkflowStaticData === 'function') {
    j = $getWorkflowStaticData('global').muvstok_last_callback || {};
  }
} catch (e) {}

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
  };
  const mapped = map[name] || '';
  return mapped ? env(mapped) : '';
}

const configuredReportUrl = envFor('CDP_RESULTADOS_SHEETS_URL');
const reportUrl =
  configuredReportUrl || (isDevWorkflow()
    ? ''
    : 'https://docs.google.com/spreadsheets/d/1ZBU2d3XVsngOYQH12yU7Mg9DcIzVet2dDmhMtZqHSOo/edit#gid=2127243308');

if (String(j.delivery_mode || '').trim().toLowerCase() === 'aggregate') {
  return [{ json: { skip: true, reason: 'aggregate_delivery' } }];
}

const ok = Number(j.succeeded_sku_count) || 0;
const fail = Number(j.failed_sku_count) || 0;
const total = Number(j.submitted_sku_count) || ok + fail;
const linhas = Number(j.detail_rows) || 0;
const found = Number(j.found_sku_count) || 0;
const noPrice = Number(j.no_price_sku_count) || 0;
const notFound = Number(j.not_found_sku_count) || 0;
const blocked = Number(j.blocked_sku_count) || 0;
const errors = Number(j.error_sku_count) || 0;
let notify = String(j.notify || j.reply_channel || '').trim().toLowerCase();
let chatId = String(j.chat_id || '').trim();
let replyEmail = String(j.reply_email || '').trim();

if (!notify) {
  if (replyEmail) notify = 'email';
  else if (chatId) notify = 'telegram';
}
if (notify === 'email') {
  chatId = '';
} else if (notify === 'telegram') {
  replyEmail = '';
}

let resumo;
if (fail > 0 && ok === 0) {
  resumo = 'Não foi possível consultar o estoque desta vez.';
} else if (total === 1) {
  resumo = '1 peça consultada.';
} else {
  resumo = total + ' peças consultadas.';
}

resumo += ' Com preço: ' + found + '.';
if (noPrice > 0) resumo += ' Sem preço: ' + noPrice + '.';
if (notFound > 0) resumo += ' Não encontradas: ' + notFound + '.';
if (blocked > 0) resumo += ' Bloqueadas: ' + blocked + '.';
if (errors > 0) resumo += ' Erros: ' + errors + '.';

if (linhas > 0) {
  resumo += ' ' + (linhas === 1 ? '1 oferta registrada' : linhas + ' ofertas registradas') + ' no relatório.';
} else if (found > 0 || noPrice > 0) {
  resumo += ' Nenhuma oferta nova no relatório.';
}

const lines = [
  '🤖 *' + ASSISTANT_NAME + '*',
  '',
  '✅ *' + ESTOQUE_LABEL + ': consulta concluída*',
  '',
  resumo,
  '',
  '📎 Relatório: ' + reportUrl,
];

if (blocked > 0 || errors > 0) {
  lines.splice(4, 0, '⚠️ Algumas fontes tiveram bloqueio ou erro.');
}

function escapeHtml(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function pctLabel(value, divisor) {
  const n = Number(value) || 0;
  const d = Number(divisor) || 0;
  return d > 0 ? ((n / d) * 100).toFixed(1) + '%' : '0.0%';
}

if (notify === 'email' && replyEmail) {
  const pct = pctLabel(found, total);
  const tone = errors > 0 || blocked > 0 ? '#b45309' : '#047857';
  const status = errors > 0 || blocked > 0 ? 'Concluída com avisos' : 'Consulta concluída';
  const html =
    '<div style="margin:0;padding:0;background:#f6f8fb;font-family:Arial,Helvetica,sans-serif;color:#1f2937">' +
    '<div style="max-width:640px;margin:0 auto;padding:28px 18px">' +
    '<div style="background:#ffffff;border:1px solid #e5e7eb;border-radius:12px;overflow:hidden">' +
    '<div style="padding:22px 24px;border-bottom:1px solid #eef2f7">' +
    '<div style="font-size:12px;text-transform:uppercase;letter-spacing:0;color:#64748b;font-weight:700">' +
    escapeHtml(ESTOQUE_LABEL) +
    '</div>' +
    '<h1 style="font-size:24px;line-height:1.25;margin:8px 0 0;color:#111827">' +
    escapeHtml(status) +
    '</h1>' +
    '</div>' +
    '<div style="padding:22px 24px">' +
    '<p style="font-size:15px;line-height:1.6;margin:0 0 18px">A consulta no Estoque Online foi finalizada.</p>' +
    '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;margin:0 0 20px">' +
    '<tr>' +
    '<td style="padding:14px 16px;background:#f8fafc;border:1px solid #e5e7eb;border-radius:8px">' +
    '<div style="font-size:12px;color:#64748b;text-transform:uppercase;font-weight:700">Peças consultadas</div>' +
    '<div style="font-size:26px;font-weight:700;color:#111827;margin-top:4px">' +
    total +
    '</div>' +
    '</td>' +
    '<td width="12"></td>' +
    '<td style="padding:14px 16px;background:#f8fafc;border:1px solid #e5e7eb;border-radius:8px">' +
    '<div style="font-size:12px;color:#64748b;text-transform:uppercase;font-weight:700">Com preço</div>' +
    '<div style="font-size:26px;font-weight:700;color:' +
    tone +
    ';margin-top:4px">' +
    found +
    '</div>' +
    '</td>' +
    '</tr>' +
    '</table>' +
    '<div style="font-size:14px;line-height:1.7;color:#475569">' +
    '<strong>Taxa com preço:</strong> ' +
    pct +
    '<br><strong>Sem preço:</strong> ' +
    noPrice +
    '<br><strong>Não encontradas:</strong> ' +
    notFound +
    '<br><strong>Bloqueadas:</strong> ' +
    blocked +
    '<br><strong>Erros:</strong> ' +
    errors +
    '</div>' +
    '<div style="background:#f8fafc;border:1px solid #e5e7eb;border-radius:8px;padding:12px 14px;margin:20px 0 0;font-size:13px;line-height:1.6;color:#475569">Este é o resultado de <strong>' +
    escapeHtml(ESTOQUE_LABEL) +
    '</strong>. O resultado de <strong>' +
    escapeHtml(WEBSCRAPERS_LABEL) +
    '</strong> chega em um e-mail separado quando a busca nos sites terminar.</div>' +
    '<p style="margin:22px 0 0"><a href="' +
    escapeHtml(reportUrl) +
    '" style="display:inline-block;background:#2563eb;color:#ffffff;text-decoration:none;border-radius:8px;padding:12px 18px;font-weight:700;font-size:14px">Abrir relatório</a></p>' +
    '</div>' +
    '</div>' +
    '<div style="font-size:12px;line-height:1.5;color:#94a3b8;text-align:center;padding:14px 0 0">Mensagem automática do Assistente CDP.</div>' +
    '</div>' +
    '</div>';

  return [
    {
      json: {
        skip: false,
        notify: 'email',
        email_to: replyEmail,
        email_subject: ASSISTANT_NAME + ' - ' + ESTOQUE_LABEL + ': consulta concluída (' + found + '/' + total + ' com preço)',
        email_html: html,
      },
    },
  ];
}

if (notify !== 'telegram' || !chatId) {
  return [{ json: { skip: true, reason: 'no_notification_target' } }];
}

return [
  {
    json: {
      skip: false,
      notify: 'telegram',
      telegram_chat_id: chatId,
      telegram_text: lines.join('\n'),
    },
  },
];
