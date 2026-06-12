// Runs after 🎲 Limitar SKUs — Assistente CDP (PT-BR). Single confirmation message.
const WEBSCRAPERS_LABEL = 'WEBSCRAPERS';
const ESTOQUE_LABEL = 'ESTOQUE ONLINE';
const dq = $input.first().json;
const total = dq.valid_skus || 0;
const sheetTotal = Number(dq.dispatch_total_before_sample || dq.total_read || 0);
const sampled = Boolean(dq.dispatch_sampled);
const skippedProcessado = Number(dq.skipped_processado || 0);
const skuCodes = (Array.isArray(dq.skus) ? dq.skus : [])
  .map((s) => String((s && s.sku) || s || '').trim().toUpperCase())
  .filter(Boolean);
const skuPreview = skuCodes.slice(0, 8).join(', ');
const skuExtra = skuCodes.length > 8 ? '\n_…e mais ' + (skuCodes.length - 8) + ' peças_' : '';

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
function envList(name) {
  const raw = env(name);
  return raw ? raw.split(',').map((s) => s.trim()).filter(Boolean) : [];
}
function estimateMins(skuCount) {
  const siteCount = envList('CDP_SCRAPER_SITES').length || 5;
  const parallel = Math.max(1, parseInt(env('CDP_SCRAPER_PARALLEL_SITES') || '3', 10) || 3);
  const waves = Math.ceil(siteCount / parallel);
  const secPerWave = Number(env('CDP_ESTIMATE_SEC_PER_WAVE') || '18') || 18;
  const interSku = Number(env('CDP_ESTIMATE_INTER_SKU_SEC') || '2.75') || 2.75;
  const totalSec = Math.max(30, Math.ceil(Math.max(1, skuCount) * (waves * secPerWave + interSku)));
  return Math.max(1, Math.ceil(totalSec / 60));
}
const mins = estimateMins(total);

function peca(n) {
  const x = Number(n) || 0;
  return x === 1 ? '1 peça' : x + ' peças';
}

let skuLine = '📦 *' + peca(total) + '* nesta rodada';
let skuEmail = String(total);
if (sampled && sheetTotal > total) {
  skuLine =
    '📦 *' +
    peca(total) +
    '* nesta rodada _(amostra aleatória de ' +
    sheetTotal.toLocaleString('pt-BR') +
    ' na fila)_';
  skuEmail = total + ' (amostra de ' + sheetTotal + ' na fila)';
}
if (skippedProcessado > 0) {
  skuLine += '\n_(+' + skippedProcessado + ' já processadas na fila, ignoradas)_';
  skuEmail += ' (+' + skippedProcessado + ' já processadas)';
}
if (skuPreview) {
  skuLine += '\n🔢 ' + skuPreview + skuExtra;
}

function looksLikeEmail(value) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(String(value || '').trim());
}
function escapeHtml(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

let origem = String(dq.origem || '').trim().toLowerCase() || 'auto';
let chatId = String(dq.telegram_chat_id || dq.chat_id || '').trim();
let emailFrom = String(dq.email_from || '').trim();
const notify = String(dq.notify || '').trim();
let commandOrigin = String(dq.command_origin || origem || '').trim().toLowerCase();
let replyChannel = String(dq.reply_channel || '').trim().toLowerCase();

if (!emailFrom && looksLikeEmail(notify)) emailFrom = notify;
if (!chatId && notify && !looksLikeEmail(notify)) chatId = notify;
if (looksLikeEmail(chatId)) {
  if (!emailFrom) emailFrom = chatId;
  chatId = '';
}
if (!replyChannel) {
  if (commandOrigin === 'email' || emailFrom) replyChannel = 'email';
  else if (commandOrigin === 'telegram' || chatId) replyChannel = 'telegram';
}

try {
  if (typeof $getWorkflowStaticData === 'function') {
    const sd = $getWorkflowStaticData('global');
    const ctx = sd.cdp_sheet_requester;
    if (ctx) {
      if (!replyChannel && ctx.reply_channel) {
        replyChannel = String(ctx.reply_channel).trim().toLowerCase();
      }
      if (!commandOrigin && ctx.command_origin) {
        commandOrigin = String(ctx.command_origin).trim().toLowerCase();
      }
      if (!emailFrom) emailFrom = String(ctx.email_from || '').trim();
      const inputIsEmail = commandOrigin === 'email' || replyChannel === 'email' || emailFrom;
      if (!inputIsEmail && !chatId) chatId = String(ctx.chat_id || '').trim();
      if (looksLikeEmail(chatId)) {
        if (!emailFrom) emailFrom = chatId;
        chatId = '';
      }
    }
  }
} catch (e) {}

try {
  const r = $('📧 Roteador de Comando').first().json;
  if (r && r.origem === 'email') {
    origem = 'email';
    commandOrigin = 'email';
    replyChannel = 'email';
    emailFrom = String(r.email_from || r.notify || '').trim();
    chatId = '';
  }
} catch (e) {}

if (origem !== 'email') {
  try {
    const em = $('🔀 Switch Comando (Email)').first().json;
    if (em && em.origem === 'email') {
      origem = 'email';
      commandOrigin = 'email';
      replyChannel = 'email';
      emailFrom = String(em.email_from || '').trim();
      chatId = '';
    }
  } catch (e) {}
}

if (!emailFrom) {
  try {
    const gm = $('Gmail Trigger').first().json;
    if (gm?.from?.value?.[0]?.address) {
      emailFrom = String(gm.from.value[0].address).trim();
      origem = 'email';
      commandOrigin = 'email';
      replyChannel = 'email';
      chatId = '';
    }
  } catch (e) {}
}

if (origem !== 'email') {
  try {
    const tg = $('🔀 Switch Comando (Telegram)').first().json;
    const route = String(tg?.route || '');
    const cid = String(tg?.chat_id || tg?.notify || '').trim();
    if (cid && !looksLikeEmail(cid)) {
      chatId = chatId || cid;
      origem = 'telegram';
      commandOrigin = 'telegram';
      replyChannel = 'telegram';
    }
    if (route === 'analisar') {
      origem = 'telegram';
      commandOrigin = 'telegram';
      replyChannel = 'telegram';
    }
  } catch (e) {}
}

if (!replyChannel) {
  if (emailFrom) replyChannel = 'email';
  else if (chatId) replyChannel = 'telegram';
}
if (replyChannel === 'email') {
  origem = 'email';
  commandOrigin = 'email';
  chatId = '';
} else if (replyChannel === 'telegram') {
  origem = 'telegram';
  commandOrigin = 'telegram';
  emailFrom = '';
}

const triggered = !!(chatId || emailFrom);
const tempo = mins === 1 ? '~1 minuto' : '~' + mins + ' minutos';

let commandLabel = '.analisar';
try {
  const route = String(dq.command_route || dq.route || '').trim();
  if (route.startsWith('sku')) commandLabel = '.sku';
} catch (e) {}
if (commandLabel === '.analisar') {
  try {
    const tg = $('🔀 Switch Comando (Telegram)').first().json;
    const r = String(tg?.route || '');
    if (r.startsWith('sku')) commandLabel = '.sku';
  } catch (e) {}
}

if (total < 1) {
  const reason =
    skippedProcessado > 0 && sheetTotal > 0 ? 'all_processed' : 'no_pending_skus';
  const pendingText =
    reason === 'all_processed'
      ? 'Todas as peças encontradas na planilha já estavam marcadas como processadas.'
      : 'A planilha CDP_SKUs não retornou peças pendentes para consulta.';
  const pendingSuffix =
    skippedProcessado > 0
      ? '\n_(' + skippedProcessado + ' já processadas foram ignoradas)_'
      : '';
  const msgTelegramEmpty = [
    '🤖 *Assistente CDP*',
    '',
    'Recebi sua consulta (*' + commandLabel + '*), mas não há peças pendentes para iniciar.',
    '',
    pendingText + pendingSuffix,
    '',
    'Atualize a planilha com novos códigos ou limpe o status PROCESSADO das peças que devem ser consultadas.',
  ].join('\n');
  const msgEmailEmptyHtml =
    '<div style="margin:0;padding:0;background:#f6f8fb;font-family:Arial,Helvetica,sans-serif;color:#1f2937">' +
    '<div style="max-width:640px;margin:0 auto;padding:28px 18px">' +
    '<div style="background:#ffffff;border:1px solid #e5e7eb;border-radius:12px;overflow:hidden">' +
    '<div style="padding:22px 24px;border-bottom:1px solid #eef2f7">' +
    '<div style="font-size:12px;text-transform:uppercase;letter-spacing:0;color:#64748b;font-weight:700">Nenhuma consulta iniciada</div>' +
    '<h1 style="font-size:24px;line-height:1.25;margin:8px 0 0;color:#111827">Não há peças pendentes</h1>' +
    '</div>' +
    '<div style="padding:22px 24px">' +
    '<p style="font-size:15px;line-height:1.6;margin:0 0 14px">Recebemos o comando <strong>' +
    escapeHtml(commandLabel) +
    '</strong>, mas nenhuma peça pendente foi encontrada para iniciar a consulta.</p>' +
    '<p style="font-size:15px;line-height:1.6;margin:0 0 14px">' +
    escapeHtml(pendingText) +
    '</p>' +
    (skippedProcessado > 0
      ? '<p style="font-size:14px;line-height:1.6;margin:0 0 14px;color:#64748b">' +
        escapeHtml(skippedProcessado + ' peças já processadas foram ignoradas.') +
        '</p>'
      : '') +
    '<p style="font-size:14px;line-height:1.6;margin:0;color:#475569">Atualize a planilha com novos códigos ou limpe o status PROCESSADO das peças que devem ser consultadas.</p>' +
    '</div>' +
    '</div>' +
    '<div style="font-size:12px;line-height:1.5;color:#94a3b8;text-align:center;padding:14px 0 0">Mensagem automática do Assistente CDP.</div>' +
    '</div>' +
    '</div>';

  return [
    {
      json: {
        total,
        mins: 0,
        origem,
        command_origin: commandOrigin || origem,
        reply_channel: replyChannel || origem,
        triggered,
        chat_id: chatId,
        email_from: emailFrom,
        notify: replyChannel === 'telegram' ? chatId : replyChannel === 'email' ? emailFrom : '',
        no_skus: true,
        skip_dispatch: true,
        no_skus_reason: reason,
        skipped_processado: skippedProcessado,
        msg_telegram: msgTelegramEmpty,
        msg_email_html: msgEmailEmptyHtml,
        msg_email_subject: 'Consulta CDP sem peças pendentes',
      },
    },
  ];
}

const msgTelegram = [
  '🤖 *Assistente CDP*',
  '',
  'Recebi sua consulta (*' + commandLabel + '*). Estamos buscando preços nos sites e no estoque.',
  '',
  skuLine,
  '⏱️ Previsão: *' + tempo + '* (sites e estoque em paralelo)',
  '',
  'Quando *' +
    WEBSCRAPERS_LABEL +
    '* e *' +
    ESTOQUE_LABEL +
    '* terminarem, você receberá *um único resultado final* com o link do relatório. ✨',
].join('\n');

const statusTone = total > 1 ? 'Consultas em andamento' : 'Consulta em andamento';
const safeCommand = escapeHtml(commandLabel);
const safeSkuPreview = escapeHtml(skuPreview);
const safeSkuEmail = escapeHtml(skuEmail);
const safeTempo = escapeHtml(tempo);
const msgEmailHtml =
  '<div style="margin:0;padding:0;background:#f6f8fb;font-family:Arial,Helvetica,sans-serif;color:#1f2937">' +
  '<div style="max-width:640px;margin:0 auto;padding:28px 18px">' +
  '<div style="background:#ffffff;border:1px solid #e5e7eb;border-radius:12px;overflow:hidden">' +
  '<div style="padding:22px 24px;border-bottom:1px solid #eef2f7">' +
  '<div style="font-size:12px;text-transform:uppercase;letter-spacing:0;color:#64748b;font-weight:700">' +
  escapeHtml(statusTone) +
  '</div>' +
  '<h1 style="font-size:24px;line-height:1.25;margin:8px 0 0;color:#111827">Consulta CDP iniciada</h1>' +
  '</div>' +
  '<div style="padding:22px 24px">' +
  '<p style="font-size:15px;line-height:1.6;margin:0 0 18px">Recebemos o comando <strong>' +
  safeCommand +
  '</strong>. A busca em sites e estoque já está em andamento.</p>' +
  '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;margin:0 0 20px">' +
  '<tr>' +
  '<td style="padding:14px 16px;background:#f8fafc;border:1px solid #e5e7eb;border-radius:8px">' +
  '<div style="font-size:12px;color:#64748b;text-transform:uppercase;font-weight:700">Peças na fila</div>' +
  '<div style="font-size:26px;font-weight:700;color:#111827;margin-top:4px">' +
  safeSkuEmail +
  '</div>' +
  '</td>' +
  '<td width="12"></td>' +
  '<td style="padding:14px 16px;background:#f8fafc;border:1px solid #e5e7eb;border-radius:8px">' +
  '<div style="font-size:12px;color:#64748b;text-transform:uppercase;font-weight:700">Previsão</div>' +
  '<div style="font-size:26px;font-weight:700;color:#111827;margin-top:4px">' +
  safeTempo +
  '</div>' +
  '</td>' +
  '</tr>' +
  '</table>' +
  '<div style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:8px;padding:14px 16px;margin:0 0 20px">' +
  '<div style="font-size:12px;color:#1d4ed8;text-transform:uppercase;font-weight:700;margin-bottom:6px">Resultado final</div>' +
  '<div style="font-size:14px;line-height:1.6;color:#1e3a8a">Quando <strong>' +
  escapeHtml(WEBSCRAPERS_LABEL) +
  '</strong> e <strong>' +
  escapeHtml(ESTOQUE_LABEL) +
  '</strong> terminarem, enviaremos <strong>um único e-mail</strong> com o resumo consolidado e o link do relatório.</div>' +
  '</div>' +
  (skuPreview
    ? '<div style="font-size:13px;color:#64748b;text-transform:uppercase;font-weight:700;margin-bottom:6px">Códigos</div>' +
      '<div style="font-size:14px;line-height:1.5;background:#f8fafc;border:1px solid #e5e7eb;border-radius:8px;padding:12px 14px;color:#111827">' +
      safeSkuPreview +
      '</div>'
    : '') +
  '<p style="font-size:14px;line-height:1.6;color:#475569;margin:20px 0 0">Aguarde o e-mail final antes de considerar a rodada encerrada.</p>' +
  '</div>' +
  '</div>' +
  '<div style="font-size:12px;line-height:1.5;color:#94a3b8;text-align:center;padding:14px 0 0">Mensagem automática do Assistente CDP.</div>' +
  '</div>' +
  '</div>';

return [
  {
    json: {
      total,
      mins,
      origem,
      command_origin: commandOrigin || origem,
      reply_channel: replyChannel || origem,
      triggered,
      chat_id: chatId,
      email_from: emailFrom,
      notify: replyChannel === 'telegram' ? chatId : replyChannel === 'email' ? emailFrom : '',
      msg_telegram: msgTelegram,
      msg_email_html: msgEmailHtml,
      msg_email_subject: 'Consulta CDP iniciada — resultado final após sites e estoque (' + peca(total) + ')',
    },
  },
];
