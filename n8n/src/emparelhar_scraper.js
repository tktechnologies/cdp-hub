// cdp_router — pair scraper HTTP responses to SKUs for sheet PROCESSADO updates.

const httpItems = $input.all();
const batches = $('⚙️ Formatar Payload Scraper').all();
const out = [];
const PROCESSING = '⏳ Processando';

for (let i = 0; i < httpItems.length; i++) {
  const resp = httpItems[i].json;
  const hasJob = Boolean(resp.job_id);
  const sc = resp.statusCode != null ? Number(resp.statusCode) : hasJob ? 200 : 0;
  if (!hasJob && (sc < 200 || sc >= 300)) continue;
  const batch = batches[i]?.json;
  if (!batch) continue;
  const rows = Array.isArray(batch.sheet_rows) ? batch.sheet_rows : batch.items || [];
  for (const it of rows) {
    if (!it || !it.sku) continue;
    const rowNumber = it.row_number;
    if (rowNumber === undefined || rowNumber === null || rowNumber === '') continue;
    out.push({
      json: {
        sku: String(it.sku).trim(),
        row_number: rowNumber,
        PROCESSADO: PROCESSING,
        ENCONTRADO: PROCESSING,
        NOTIFICADO: PROCESSING,
      },
    });
  }
}
return out;
