// cdp_notifier — build job-scoped UTF-8 CSV for aggregate final email attachment.

function numericPrice(value) {
  if (value === null || value === undefined || value === '') return null;
  const n = Number(value);
  return Number.isFinite(n) && n > 0 ? n : null;
}

function partHasValidPrice(part) {
  return !!(part && part.exact_match && numericPrice(part.price) !== null);
}

function siteParts(site) {
  if (Array.isArray(site?.results)) return site.results;
  if (Array.isArray(site?.parts)) return site.parts;
  return [];
}

function siteHasValidPrice(site) {
  if (site?.has_valid_price === true || String(site?.sku_result || '').toUpperCase() === 'FOUND_PRICE') {
    return true;
  }
  return siteParts(site).some(partHasValidPrice);
}

function siteHasExactEvidence(site) {
  if (String(site?.sku_result || '').toUpperCase() === 'NO_PRICE') return true;
  if (String(site?.status || '').toLowerCase() === 'no_price') return true;
  return siteParts(site).some((part) => !!part?.exact_match);
}

function skuHasValidPrice(row) {
  if (row?.has_valid_price === true || String(row?.sku_result || '').toUpperCase() === 'FOUND_PRICE') {
    return true;
  }
  const best = row?.best_price || null;
  if (best && best.exact_match !== false && numericPrice(best.price) !== null) return true;
  return (Array.isArray(row?.site_results) ? row.site_results : []).some(siteHasValidPrice);
}

function canonicalSkuStatus(row) {
  const explicit = String(row?.sku_result || '').trim().toUpperCase();
  if (explicit) return explicit;
  const sites = Array.isArray(row?.site_results) ? row.site_results : [];
  if (skuHasValidPrice(row)) return 'FOUND_PRICE';
  if (row?.has_any_exact_evidence === true || sites.some(siteHasExactEvidence)) return 'NO_PRICE';
  const statuses = sites.map((site) => String(site?.sku_result || site?.status || '').trim().toUpperCase());
  if (statuses.includes('BLOCKED')) return 'BLOCKED';
  if (statuses.includes('TIMEOUT')) return 'TIMEOUT';
  if (statuses.includes('ERROR')) return 'ERROR';
  return 'NOT_FOUND';
}

function bestExactOffer(skuResult) {
  let bestPrice = null;
  let bestSite = '';
  let bestUrl = '';
  for (const sr of skuResult.site_results || []) {
    for (const part of sr.results || []) {
      if (!partHasValidPrice(part)) continue;
      const price = numericPrice(part.price);
      if (bestPrice === null || price < bestPrice) {
        bestPrice = price;
        bestSite = sr.site_name || sr.site || '';
        bestUrl = part.product_url || '';
      }
    }
  }
  return { bestPrice, bestSite, bestUrl };
}

function statusLabel(status) {
  if (status === 'FOUND_PRICE') return 'Encontrado';
  if (status === 'NO_PRICE') return 'Sem preco';
  if (status === 'BLOCKED') return 'Bloqueado';
  if (status === 'TIMEOUT' || status === 'ERROR') return 'Erro';
  return 'Sem resultado';
}

function csvEscape(val) {
  const s = String(val ?? '');
  if (/[;\r\n"]/.test(s)) return '"' + s.replace(/"/g, '""') + '"';
  return s;
}

const fmt = $('📣 Formatar mensagem final').first().json;
const jobPayload = $input.first().json;
const results = Array.isArray(jobPayload.results) ? jobPayload.results : [];
const batchGroupId = String(fmt.batch_group_id || 'job').trim();
const jobId = String(jobPayload.job_id || fmt.scraper_job_id || 'unknown').trim();
const dateStamp = new Date().toISOString().slice(0, 10);

const rows = [];
for (const skuResult of results) {
  const sku = skuResult.sku || '';
  const canonical = canonicalSkuStatus(skuResult);
  const offer = canonical === 'FOUND_PRICE' ? bestExactOffer(skuResult) : { bestPrice: null, bestSite: '', bestUrl: '' };
  const siteSummary = [];
  for (const sr of skuResult.site_results || []) {
    const siteName = sr.site_name || sr.site || '';
    const srStatus = String(sr.sku_result || sr.status || '').toLowerCase() || 'sem_resultado';
    siteSummary.push(siteName + (siteHasValidPrice(sr) ? ' OK' : ' ' + srStatus));
  }
  rows.push({
    SKU: sku,
    STATUS: statusLabel(canonical),
    'MELHOR PREÇO':
      offer.bestPrice !== null
        ? 'BRL ' + Number(offer.bestPrice).toLocaleString('pt-BR', { minimumFractionDigits: 2 })
        : 'N/A',
    SITE: offer.bestSite || 'N/A',
    LINK: offer.bestUrl || 'N/A',
    'SITES CHECADOS': siteSummary.join(' | '),
    DATA: new Date().toLocaleDateString('pt-BR'),
  });
}

const header = ['SKU', 'STATUS', 'MELHOR PREÇO', 'SITE', 'LINK', 'SITES CHECADOS', 'DATA'];
const csvLines = [header.map(csvEscape).join(';')];
for (const row of rows) {
  csvLines.push(header.map((h) => csvEscape(row[h] ?? '')).join(';'));
}
const csvText = '\ufeff' + csvLines.join('\r\n');
const b64 = Buffer.from(csvText, 'utf8').toString('base64');
const fname = `cdp_${batchGroupId}_${dateStamp}.csv`;

return [
  {
    json: {
      ...fmt,
      csv_filename: fname,
      csv_row_count: rows.length,
    },
    binary: {
      data: {
        data: b64,
        mimeType: 'text/csv; charset=utf-8',
        fileName: fname,
        fileExtension: 'csv',
      },
    },
  },
];
