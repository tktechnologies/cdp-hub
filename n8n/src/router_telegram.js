// ─── Telegram Command Router v4 — adds .status / .andamento ─────────────────

function env(name) {
  try {
    const raw = (typeof process !== 'undefined' && process.env && process.env[name]) || '';
    return raw.split(',').map((s) => s.trim()).filter(Boolean);
  } catch (e) {
    return [];
  }
}

function envList(name) {
  return env(name);
}

function statusCommands() {
  const raw = env('CDP_STATUS_COMMANDS');
  if (raw.length) return raw;
  return ['.status', '.andamento', '.progresso'];
}

const msg = $input.first().json;
const chatId = String(msg.message?.chat?.id || '');
const username = String(msg.message?.from?.username || msg.message?.from?.first_name || '');
const text = String(msg.message?.text || msg.message?.caption || '').trim();
const doc = msg.message?.document || null;
const hasFile = !!doc;

const allowed = envList('TELEGRAM_ALLOWED_CHAT_IDS');
if (allowed.length && !allowed.includes(chatId)) {
  return [{ json: { route: 'unauthorized', chat_id: chatId } }];
}

const lower = text.toLowerCase();
const isAnalisar = lower.startsWith('.analisar');
const isSku = lower.startsWith('.sku');
const isStatus = statusCommands().some((cmd) => lower.startsWith(cmd.toLowerCase()));

if (isStatus) {
  return [
    {
      json: {
        route: 'status',
        chat_id: chatId,
        username,
        origem: 'telegram',
        notify: chatId,
      },
    },
  ];
}

if (isSku || hasFile) {
  const afterCmd = isSku ? text.slice(4).trim() : '';
  const textSkus = afterCmd
    .split(/[\n,;\s]+/)
    .map((s) => s.trim().toUpperCase())
    .filter((s) => /^[A-Z0-9]{5,}$/.test(s))
    .slice(0, 200);

  if (hasFile && textSkus.length > 0) {
    return [
      {
        json: {
          route: 'sku_both',
          chat_id: chatId,
          username,
          text_skus: textSkus,
          file_id: doc.file_id,
          file_name: doc.file_name || 'attachment',
          origem: 'telegram',
          notify: chatId,
        },
      },
    ];
  }
  if (hasFile && textSkus.length === 0) {
    return [
      {
        json: {
          route: 'sku_file',
          chat_id: chatId,
          username,
          text_skus: [],
          file_id: doc.file_id,
          file_name: doc.file_name || 'attachment',
          origem: 'telegram',
          notify: chatId,
        },
      },
    ];
  }
  if (!hasFile && textSkus.length > 0) {
    return [
      {
        json: {
          route: 'sku_text',
          chat_id: chatId,
          username,
          text_skus: textSkus,
          origem: 'telegram',
          notify: chatId,
        },
      },
    ];
  }
  return [
    {
      json: {
        route: 'sku_empty',
        chat_id: chatId,
        username,
        origem: 'telegram',
        notify: chatId,
      },
    },
  ];
}

if (isAnalisar) {
  return [
    {
      json: {
        route: 'analisar',
        chat_id: chatId,
        username,
        is_full_sheet_trigger: true,
        origem: 'telegram',
        notify: chatId,
      },
    },
  ];
}

return [{ json: { route: 'ignore', chat_id: chatId } }];
