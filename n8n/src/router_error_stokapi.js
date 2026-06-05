const resp = $input.first().json;
let prep = {};
try {
  prep = $('📤 Router: API Diversos').first().json;
} catch (e) {}

let chatId = String(prep.chat_id || '').trim();
let statusCode = resp.statusCode ?? resp.status_code ?? 'N/A';
let errorText = resp.error || resp.message || resp.detail || '';

if (resp.parallel_dispatch) {
  const stokapi = resp.stokapi_response || {};
  if (stokapi.accepted || stokapi.skipped) return [];
  chatId = String(resp.chat_id || '').trim();
  statusCode = stokapi.statusCode ?? 'N/A';
  errorText = stokapi.error || stokapi.body?.detail || stokapi.body?.message || 'dispatch_not_accepted';
}

if (!chatId || prep.skip_stokapi || prep.skip_muvstok) return [];
const msg = [
  '🤖 *Assistente CDP*',
  '',
  '⚠️ A consulta de estoque não iniciou nesta rodada.',
  'A busca em sites continua — você receberá o aviso de sites normalmente.',
  statusCode !== 'N/A' || errorText ? 'Erro: HTTP ' + statusCode + ' — ' + String(errorText).slice(0, 160) : '',
  '',
  'Se o problema persistir, tente novamente em alguns minutos.',
].filter((line) => line !== '').join('\n');
return [{ json: { chat_id: chatId, msg } }];
