// cdp_router — format API Diversos dispatch failures for Telegram or email requester.

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
      return String($workflow.name);
    }
  } catch (e) {}
  return '';
}

function isDevWorkflow() {
  return workflowName().trim().toLowerCase().startsWith('dev -');
}

function envFor(name) {
  if (isDevWorkflow() && name === 'NOTIFICATION_EMAIL_TO') {
    return env('CDP_DEV_NOTIFICATION_EMAIL_TO');
  }
  return env(name);
}

function escapeHtml(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function compactError(value) {
  if (value === null || value === undefined || value === '') return '';
  if (typeof value === 'string') return value;
  if (typeof value !== 'object') return String(value);
  const nested =
    value.message ||
    value.detail ||
    value.error ||
    value.description ||
    value.body?.detail ||
    value.body?.message ||
    value.body?.error ||
    value.response?.body?.detail ||
    value.response?.body?.message ||
    value.response?.body?.error ||
    value.response?.data?.detail ||
    value.response?.data?.message ||
    value.response?.data?.error;
  if (nested && nested !== value) {
    const compact = compactError(nested);
    if (compact) return compact;
  }
  try {
    return JSON.stringify(value);
  } catch (e) {
    return String(value);
  }
}

function firstStatusCode(...values) {
  for (const value of values) {
    if (value === null || value === undefined || value === '') continue;
    const n = Number(value);
    return Number.isFinite(n) ? n : value;
  }
  return 'N/A';
}

const resp = $input.first().json;
let prep = {};
try {
  prep = $('📤 Router: API Diversos').first().json;
} catch (e) {}

let chatId = String(prep.chat_id || '').trim();
let replyEmail = String(prep.reply_email || prep.email_from || '').trim();
let replyChannel = String(prep.reply_channel || prep.command_origin || '').trim().toLowerCase();
let statusCode = firstStatusCode(
  resp.statusCode,
  resp.status_code,
  resp.error?.statusCode,
  resp.error?.status,
  resp.response?.statusCode,
  resp.response?.status
);
let errorText = compactError(resp.error || resp.message || resp.detail || resp.body || resp);

if (resp.parallel_dispatch) {
  const stokapi = resp.stokapi_response || {};
  if (stokapi.accepted || stokapi.skipped) return [];
  chatId = String(resp.chat_id || prep.chat_id || '').trim();
  replyEmail = String(resp.reply_email || prep.reply_email || prep.email_from || '').trim();
  replyChannel = String(resp.reply_channel || prep.reply_channel || prep.command_origin || replyChannel)
    .trim()
    .toLowerCase();
  statusCode = firstStatusCode(
    stokapi.statusCode,
    stokapi.status_code,
    stokapi.error?.statusCode,
    stokapi.error?.status,
    stokapi.response?.statusCode,
    stokapi.response?.status
  );
  errorText =
    compactError(stokapi.error || stokapi.body || stokapi.response || stokapi) ||
    'dispatch_not_accepted';
}

if (prep.skip_stokapi || prep.skip_muvstok) return [];

if (replyChannel === 'email') {
  chatId = '';
} else if (replyChannel === 'telegram') {
  replyEmail = '';
} else if (replyEmail) {
  replyChannel = 'email';
} else if (chatId) {
  replyChannel = 'telegram';
}

if (!chatId && !replyEmail) return [];

const detail =
  statusCode !== 'N/A' || errorText
    ? 'Erro: HTTP ' + statusCode + ' — ' + compactError(errorText).slice(0, 160)
    : '';

const msg = [
  '🤖 *Assistente CDP*',
  '',
  '⚠️ A consulta de estoque não iniciou nesta rodada.',
  'A busca em sites continua — você receberá o aviso de sites normalmente.',
  detail,
  '',
  'Se o problema persistir, tente novamente em alguns minutos.',
]
  .filter((line) => line !== '')
  .join('\n');

const html =
  '<div style="font-family:Arial,sans-serif;color:#1f2937;max-width:640px">' +
  '<h2 style="margin:0 0 12px">Consulta de estoque não iniciou</h2>' +
  '<p style="margin:0 0 12px;line-height:1.6">A busca em sites continua. Você receberá o resultado consolidado quando a consulta de sites terminar.</p>' +
  (detail
    ? '<p style="margin:0 0 12px;color:#b45309"><strong>' + escapeHtml(detail) + '</strong></p>'
    : '') +
  '<p style="margin:0;color:#64748b;font-size:13px">Se o problema persistir, tente novamente em alguns minutos.</p>' +
  '</div>';

return [
  {
    json: {
      chat_id: chatId,
      email_to: replyEmail,
      reply_channel: replyChannel || (replyEmail ? 'email' : 'telegram'),
      msg,
      msg_email_subject: 'CDP — consulta de estoque não iniciou',
      msg_email_html: html,
    },
  },
];
