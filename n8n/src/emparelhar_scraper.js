// cdp_router — pair scraper HTTP responses to SKUs for sheet PROCESSADO updates.

const PROCESSING = '⏳ Processando';
const updatesByRow = {};

function responseAccepted(resp) {
  return Boolean(resp && (resp.accepted || resp.job_id || resp.body?.job_id));
}

function pushRowsForBatch(batch, updatesByRow) {
  const rows = Array.isArray(batch.sheet_rows) ? batch.sheet_rows : batch.items || [];
  for (const it of rows) {
    if (!it || !it.sku) continue;
    const rowNumber = it.row_number;
    if (rowNumber === undefined || rowNumber === null || rowNumber === '') continue;
    updatesByRow[rowNumber] = {
      PROCESSADO: PROCESSING,
      ENCONTRADO: PROCESSING,
      NOTIFICADO: PROCESSING,
    };
  }
}

function mergeWithSheetRows(updatesByRow) {
  let sheetItems = [];
  try {
    sheetItems = $('📊 Ler CDP_SKUs').all();
  } catch (e) {
    sheetItems = [];
  }
  if (!sheetItems.length) {
    return Object.entries(updatesByRow).map(([rowNumber, values]) => ({
      json: {
        row_number: Number(rowNumber),
        ...values,
      },
    }));
  }
  const merged = [];
  for (let i = 0; i < sheetItems.length; i++) {
    const item = sheetItems[i];
    const row = item.json || {};
    const rn = row.row_number;
    const upd = updatesByRow[rn];
    if (!upd) continue;
    merged.push({
      json: {
        ...row,
        PROCESSADO: upd.PROCESSADO,
        ENCONTRADO: upd.ENCONTRADO,
        NOTIFICADO: upd.NOTIFICADO,
      },
      pairedItem: item.pairedItem ?? { item: i },
    });
  }
  return merged;
}

const first = $input.first().json || {};
if (first.parallel_dispatch) {
  const responses = Array.isArray(first.scraper_responses) ? first.scraper_responses : [];
  const batches = Array.isArray(first.scraper_batches) ? first.scraper_batches : [];
  for (let i = 0; i < responses.length; i++) {
    const resp = responses[i];
    if (!responseAccepted(resp)) continue;
    const batch =
      batches.find((b) => Number(b.batch_index) === Number(resp.batch_index)) || batches[i];
    if (batch) pushRowsForBatch(batch, updatesByRow);
  }
  return mergeWithSheetRows(updatesByRow);
}

const httpItems = $input.all();
const batches = $('⚙️ Formatar Payload Scraper').all();

for (let i = 0; i < httpItems.length; i++) {
  const resp = httpItems[i].json;
  const hasJob = Boolean(resp.job_id);
  const sc = resp.statusCode != null ? Number(resp.statusCode) : hasJob ? 200 : 0;
  if (!hasJob && (sc < 200 || sc >= 300)) continue;
  const batch = batches[i]?.json;
  if (!batch) continue;
  pushRowsForBatch(batch, updatesByRow);
}
return mergeWithSheetRows(updatesByRow);
