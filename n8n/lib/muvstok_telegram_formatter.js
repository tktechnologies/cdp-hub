// User-facing Telegram copy for API Diversos completion (injected into cdp_stokapi).
const ASSISTANT_NAME = 'Assistente CDP';

let j = {};
try {
  if (typeof $getWorkflowStaticData === 'function') {
    j = $getWorkflowStaticData('global').muvstok_last_callback || {};
  }
} catch (e) {}

if (j.notify !== 'telegram' || !j.chat_id) {
  return [{ json: { skip: true, reason: 'no_telegram_target' } }];
}

function env(name) {
  try {
    if (typeof process !== 'undefined' && process.env && process.env[name]) {
      return String(process.env[name]).trim();
    }
  } catch (e) {}
  return '';
}

const reportUrl =
  env('CDP_RESULTADOS_SHEETS_URL') ||
  'https://docs.google.com/spreadsheets/d/1ZBU2d3XVsngOYQH12yU7Mg9DcIzVet2dDmhMtZqHSOo/edit#gid=533358674';

const ok = Number(j.succeeded_sku_count) || 0;
const fail = Number(j.failed_sku_count) || 0;
const total = Number(j.submitted_sku_count) || ok + fail;
const linhas = Number(j.detail_rows) || 0;

let resumo;
if (fail > 0 && ok === 0) {
  resumo = 'Não foi possível consultar o estoque desta vez.';
} else if (fail > 0) {
  resumo = ok + ' de ' + total + ' peças consultadas com sucesso.';
} else if (total === 1) {
  resumo = '1 peça consultada.';
} else {
  resumo = total + ' peças consultadas.';
}

if (linhas > 0) {
  resumo += ' ' + (linhas === 1 ? '1 oferta registrada' : linhas + ' ofertas registradas') + ' no relatório.';
} else if (ok > 0) {
  resumo += ' Nenhuma oferta nova no relatório.';
}

const lines = [
  '🤖 *' + ASSISTANT_NAME + '*',
  '',
  '✅ *Consulta de estoque concluída*',
  '',
  resumo,
  '',
  '📎 Relatório: ' + reportUrl,
];

if (fail > 0) {
  lines.splice(4, 0, '⚠️ Alguns itens não retornaram dados.');
}

return [
  {
    json: {
      skip: false,
      telegram_chat_id: j.chat_id,
      telegram_text: lines.join('\n'),
    },
  },
];
