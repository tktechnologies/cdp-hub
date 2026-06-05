// cdp_router - persist requester channel before reading CDP_SKUs.

function looksLikeEmail(value) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(String(value || '').trim());
}

const d = $input.first().json;
let chatId = String(d.chat_id || d.telegram_chat_id || '').trim();
let emailFrom = String(d.email_from || '').trim();
const notifyRaw = String(d.notify || '').trim();
let commandOrigin = String(d.command_origin || d.origem || '').trim().toLowerCase();
let replyChannel = String(d.reply_channel || '').trim().toLowerCase();

if (!emailFrom && looksLikeEmail(notifyRaw)) emailFrom = notifyRaw;
if (!chatId && notifyRaw && !looksLikeEmail(notifyRaw)) chatId = notifyRaw;

if (!replyChannel) {
  if (commandOrigin === 'email' || emailFrom) replyChannel = 'email';
  else if (commandOrigin === 'telegram' || chatId) replyChannel = 'telegram';
}
if (!commandOrigin && replyChannel) commandOrigin = replyChannel;

let notify = 'none';
if (replyChannel === 'email') {
  notify = 'email';
  commandOrigin = 'email';
  chatId = '';
} else if (replyChannel === 'telegram') {
  notify = 'telegram';
  commandOrigin = 'telegram';
  emailFrom = '';
} else if (chatId) {
  replyChannel = 'telegram';
  commandOrigin = commandOrigin || 'telegram';
  notify = 'telegram';
} else if (emailFrom) {
  replyChannel = 'email';
  commandOrigin = commandOrigin || 'email';
  notify = 'email';
}

try {
  if (typeof $getWorkflowStaticData === 'function') {
    const sd = $getWorkflowStaticData('global');
    sd.cdp_sheet_requester = {
      chat_id: chatId,
      email_from: emailFrom,
      notify,
      reply_channel: replyChannel || notify,
      command_origin: commandOrigin || replyChannel || notify,
    };
  }
} catch (e) {}

return [
  {
    json: {
      ...d,
      chat_id: chatId,
      email_from: emailFrom,
      notify,
      reply_channel: replyChannel || notify,
      command_origin: commandOrigin || replyChannel || notify,
    },
  },
];
