// Runs after 🎲 Limitar SKUs — Assistente CDP (PT-BR). Single confirmation message.
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

let origem = 'auto';
let chatId = String(dq.telegram_chat_id || dq.chat_id || dq.notify || '').trim();
let emailFrom = String(dq.email_from || '').trim();

try {
  if (typeof $getWorkflowStaticData === 'function') {
    const sd = $getWorkflowStaticData('global');
    const ctx = sd.cdp_sheet_requester;
    if (ctx) {
      if (!chatId) chatId = String(ctx.chat_id || '').trim();
      if (!emailFrom) emailFrom = String(ctx.email_from || '').trim();
      if (chatId) origem = 'telegram';
      else if (emailFrom) origem = 'email';
    }
  }
} catch (e) {}

try {
  const r = $('📧 Roteador de Comando').first().json;
  if (r && r.route === 'analisar') {
    origem = 'email';
    emailFrom = String(r.email_from || r.notify || '').trim();
  }
} catch (e) {}

if (origem !== 'email') {
  try {
    const em = $('🔀 Switch Comando (Email)').first().json;
    if (em && em.route === 'analisar') {
      origem = 'email';
      emailFrom = String(em.email_from || '').trim();
    }
  } catch (e) {}
}

if (!emailFrom) {
  try {
    const gm = $('Gmail Trigger').first().json;
    if (gm?.from?.value?.[0]?.address) {
      emailFrom = String(gm.from.value[0].address).trim();
      origem = 'email';
    }
  } catch (e) {}
}

if (origem !== 'email') {
  try {
    const tg = $('🔀 Switch Comando (Telegram)').first().json;
    const route = String(tg?.route || '');
    const cid = String(tg?.chat_id || tg?.notify || '').trim();
    if (cid) {
      chatId = chatId || cid;
      origem = 'telegram';
    }
    if (route === 'analisar') origem = 'telegram';
  } catch (e) {}
}

if (origem === 'telegram' && !chatId && emailFrom) origem = 'email';

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

const msgTelegram = [
  '🤖 *Assistente CDP*',
  '',
  'Recebi sua consulta (*' + commandLabel + '*). Estamos buscando preços nos sites e no estoque.',
  '',
  skuLine,
  '⏱️ Previsão: *' + tempo + '* (sites e estoque em paralelo)',
  '',
  'Você receberá dois avisos quando terminar (sites e estoque). ✨',
].join('\n');

const msgEmailHtml =
  '<h2>Assistente CDP</h2><p>Recebemos seu <strong>' +
  commandLabel +
  '</strong> — busca em <strong>sites e estoque</strong> iniciada.</p>' +
  '<p><strong>Peças na fila:</strong> ' +
  skuEmail +
  '</p>' +
  (skuPreview ? '<p><strong>Códigos:</strong> ' + skuPreview + '</p>' : '') +
  '<p><strong>Previsão:</strong> ' +
  tempo +
  ' (sites e estoque em paralelo)</p>' +
  '<p>Você receberá dois e-mails de conclusão (sites + estoque).</p>' +
  '<p style="color:#718096;font-size:12px">— Assistente CDP (TKTech)</p>';

return [
  {
    json: {
      total,
      mins,
      origem,
      triggered,
      chat_id: chatId,
      email_from: emailFrom,
      notify: chatId || emailFrom,
      msg_telegram: msgTelegram,
      msg_email_html: msgEmailHtml,
      msg_email_subject: 'Assistente CDP — consulta iniciada (' + total + ' peças)',
    },
  },
];
