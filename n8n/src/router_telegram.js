// ─── Telegram Command Router v4 — adds .status / .andamento ─────────────────

const DEFAULT_SCRAPER_API_BASE =
  'https://cdp-scrapers-api-prod.bravecoast-b14d791e.eastus2.azurecontainerapps.io';

function envValue(name) {
  try {
    if (typeof $env !== 'undefined' && $env && $env[name]) {
      return String($env[name]).trim();
    }
  } catch (e) {
    return '';
  }
  try {
    if (typeof process !== 'undefined' && process.env && process.env[name]) {
      return String(process.env[name]).trim();
    }
  } catch (e) {
    return '';
  }
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
  return /^DEV\s*-/i.test(workflowName()) || /^dev$/i.test(envValue('CDP_ENV'));
}
function devEnvName(name) {
  const map = {
    CDP_SCRAPER_API_BASE: 'CDP_DEV_SCRAPER_API_BASE',
    MUVSTOK_SCRAPER_API_BASE: 'CDP_DEV_SCRAPER_API_BASE',
    CDP_API_KEY: 'CDP_DEV_API_KEY',
    MUVSTOK_API_KEY: 'CDP_DEV_API_KEY',
    API_KEY: 'CDP_DEV_API_KEY',
    TELEGRAM_ALLOWED_CHAT_IDS: 'TELEGRAM_DEV_ALLOWED_CHAT_IDS',
    TELEGRAM_BOT_TOKEN: 'TELEGRAM_DEV_BOT_TOKEN',
    TELEGRAM_TOKEN: 'TELEGRAM_DEV_BOT_TOKEN',
    TELEGRAM_API_TOKEN: 'TELEGRAM_DEV_BOT_TOKEN',
    CDP_STATUS_COMMANDS: 'CDP_DEV_STATUS_COMMANDS',
  };
  return map[name] || '';
}
function envFor(name) {
  if (!isDevWorkflow()) return envValue(name);
  const mapped = devEnvName(name);
  const value = mapped ? envValue(mapped) : '';
  if (value) return value;
  if (name === 'CDP_STATUS_COMMANDS') return envValue(name);
  return '';
}

function envList(name) {
  const raw = envFor(name);
  return raw ? raw.split(',').map((s) => s.trim()).filter(Boolean) : [];
}

function statusCommands() {
  const raw = envList('CDP_STATUS_COMMANDS');
  if (raw.length) return raw;
  return ['.status', '.andamento', '.progresso'];
}

function trimTrailingSlashes(value) {
  let out = String(value || '').trim();
  while (out.endsWith('/')) out = out.slice(0, -1);
  return out;
}

function scraperApiBase() {
  return trimTrailingSlashes(
    envFor('CDP_SCRAPER_API_BASE') ||
      envFor('MUVSTOK_SCRAPER_API_BASE') ||
      (isDevWorkflow() ? '' : DEFAULT_SCRAPER_API_BASE)
  );
}

function cdpApiKey() {
  return envFor('CDP_API_KEY') || envFor('MUVSTOK_API_KEY') || envFor('API_KEY');
}

function telegramBotToken() {
  return (
    envFor('TELEGRAM_BOT_TOKEN') ||
    envFor('TELEGRAM_TOKEN') ||
    envFor('TELEGRAM_API_TOKEN')
  );
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
  const base = scraperApiBase();
  return [
    {
      json: {
        route: 'status',
        chat_id: chatId,
        username,
        origem: 'telegram',
        notify: chatId,
        dispatch_runs_lookup_url:
          base + '/api/v1/dispatch-runs/active/for-chat/' + encodeURIComponent(chatId),
        dispatch_runs_api_key: cdpApiKey(),
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
          telegram_bot_token: telegramBotToken(),
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
          telegram_bot_token: telegramBotToken(),
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
