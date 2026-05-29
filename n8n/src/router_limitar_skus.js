// cdp_router — pass SKUs through; optional random sample via CDP_DISPATCH_SAMPLE_SIZE (0 = all).

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
function envInt(name, defaultVal) {
  const raw = env(name);
  if (!raw) return defaultVal;
  const n = parseInt(raw, 10);
  return Number.isFinite(n) && n >= 0 ? n : defaultVal;
}

const data = $input.first().json;
const all = Array.isArray(data.skus) ? data.skus : [];
const maxSkus = envInt('CDP_DISPATCH_SAMPLE_SIZE', 0);
let skus = all;
let sampled = false;
if (maxSkus > 0 && all.length > maxSkus) {
  const copy = [...all];
  for (let i = copy.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    const tmp = copy[i];
    copy[i] = copy[j];
    copy[j] = tmp;
  }
  skus = copy.slice(0, maxSkus);
  sampled = true;
}

const batchGroupId = 'bg-' + Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 8);
try {
  if (typeof $getWorkflowStaticData === 'function') {
    const sd = $getWorkflowStaticData('global');
    sd.cdp_last_batch_group_id = batchGroupId;
  }
} catch (e) {}

let commandRoute = 'analisar';
try {
  const tg = $('🔀 Switch Comando (Telegram)').first().json;
  if (tg && tg.route) commandRoute = String(tg.route);
} catch (e) {}
if (commandRoute === 'analisar') {
  try {
    const em = $('🔀 Switch Comando (Email)').first().json;
    if (em && em.route) commandRoute = String(em.route);
  } catch (e) {}
}

return [
  {
    json: {
      ...data,
      skus,
      valid_skus: skus.length,
      dispatch_sampled: sampled,
      dispatch_sample_limit: maxSkus,
      dispatch_total_before_sample: all.length,
      batch_group_id: batchGroupId,
      command_route: commandRoute,
    },
  },
];
