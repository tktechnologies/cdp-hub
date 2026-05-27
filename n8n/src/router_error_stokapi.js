const prep = $('📤 Router: API Diversos').first().json;
const resp = $input.first().json;
const chatId = String(prep.chat_id || '').trim();
if (!chatId || prep.skip_stokapi || prep.skip_muvstok) return [{ json: { skip: true } }];
const msg = [
  '🤖 *Assistente CDP*',
  '',
  '⚠️ A consulta de estoque não iniciou nesta rodada.',
  'A busca em sites continua — você receberá o aviso de sites normalmente.',
  '',
  'Se o problema persistir, tente novamente em alguns minutos.',
].join('\n');
return [{ json: { chat_id: chatId, msg } }];
