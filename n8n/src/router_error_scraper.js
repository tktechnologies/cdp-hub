// cdp_router - format Scraper dispatch failures for Historico and optional email alert.

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
  return workflowName().trim().toLowerCase().startsWith('dev -') || env('CDP_ENV').toLowerCase() === 'dev';
}

function envFor(name) {
  if (isDevWorkflow() && name === 'NOTIFICATION_EMAIL_TO') {
    return env('CDP_DEV_NOTIFICATION_EMAIL_TO');
  }
  return env(name);
}

function compactError(resp) {
  const raw =
    resp.error ||
    resp.message ||
    resp.detail ||
    resp.body?.detail ||
    resp.body?.message ||
    resp.body?.error ||
    JSON.stringify(resp).substring(0, 500);
  return typeof raw === 'string' ? raw : JSON.stringify(raw);
}

function historicoFromError(item, resp, batch) {
  const nowIso = new Date().toISOString();
  const batchIndex = resp.batch_index || batch?.batch_index || 'unknown';
  const totalBatches = resp.total_batches || batch?.total_batches || 'unknown';
  const statusCode = resp.statusCode ?? resp.status_code ?? 'N/A';
  const errorMsg = compactError(resp);
  const items = Array.isArray(batch?.items) ? batch.items : Array.isArray(item.items) ? item.items : [];
  const batchSize = Number(resp.batch_size || batch?.batch_size || items.length || 0);
  const emailTo = String(
    item.reply_email || item.email_from || item.email || envFor('NOTIFICATION_EMAIL_TO') || ''
  ).trim();

  let html = '<h2>CDP Job Dispatcher - Scraper API Error</h2>';
  html += '<p><strong>Time:</strong> ' + nowIso + '</p>';
  html += '<p><strong>Batch:</strong> ' + batchIndex + ' / ' + totalBatches + '</p>';
  html += '<p><strong>HTTP Status:</strong> ' + statusCode + '</p>';
  html += '<p><strong>Error:</strong></p>';
  html += '<pre style="background:#fee2e2;padding:12px;border-radius:8px">' + errorMsg + '</pre>';
  html += '<p style="color:#718096;font-size:12px">Automated alert from CDP Job Dispatcher.</p>';

  return {
    job_id: String(resp.job_id || 'dispatch-scraper-batch-' + batchIndex),
    origem: 'dispatcher_error_scraper',
    solicitante: String(item.reply_email || item.email_from || item.chat_id || ''),
    disparado_em: String(resp.started_at || item.dispatched_at || nowIso),
    concluido_em: nowIso,
    tempo_segundos: '0',
    status: '❌ ERRO_DISPATCH',
    skus_lidos: String(batchSize),
    skus_validos: String(batchSize),
    skus_encontrados: '0',
    skus_falhos: String(batchSize),
    taxa_sucesso_sku: '0%',
    taxa_sucesso_sites: '0%',
    sites_pesquisados: String(Array.isArray(batch?.sites) ? batch.sites.length : 0),
    resumo_sites: '{}',
    lista_skus_csv: String(items.map((i) => i.sku).filter(Boolean).join(', ')),
    skus_repetidos: '—',
    job_error: '[HTTP ' + statusCode + '] ' + String(errorMsg).substring(0, 1000),
    email_from: emailTo,
    email_subject: 'Dispatcher Error - Scraper batch ' + batchIndex,
    email_html: html,
  };
}

const item = $input.first().json || {};

if (item.parallel_dispatch) {
  const responses = Array.isArray(item.scraper_responses) ? item.scraper_responses : [];
  const batches = Array.isArray(item.scraper_batches) ? item.scraper_batches : [];
  return responses
    .filter((resp) => !resp.accepted)
    .map((resp, index) => {
      const batch =
        batches.find((b) => Number(b.batch_index) === Number(resp.batch_index)) || batches[index] || {};
      return { json: historicoFromError(item, resp, batch) };
    });
}

return [{ json: historicoFromError(item, item, item) }];
