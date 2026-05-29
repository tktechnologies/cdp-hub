// cdp_router — validate sheet rows, keep duplicate SKUs as real work items.
// Duplicate rows are intentionally preserved so every sheet row can receive data.

const raw = $input.all();
const seen = new Set();
const valid = [];
const dqIssues = [];
let skippedProcessado = 0;

function normalizeStatus(value) {
  return String(value || '')
    .trim()
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9]+/g, ' ')
    .trim();
}

for (const item of raw) {
  const row = item.json;
  const rawSku = row.CODIGO ?? row.SKU ?? row.sku ?? row.codigo;
  const sku = rawSku ? String(rawSku).trim().toUpperCase() : '';

  const processado = normalizeStatus(row.PROCESSADO);
  if (processado === 'processado' || processado === 'sim' || processado === 'true') {
    skippedProcessado++;
    continue;
  }

  if (!sku) {
    dqIssues.push({ issue: 'EMPTY_SKU', row: JSON.stringify(row) });
    continue;
  }
  if (sku.length < 3) {
    dqIssues.push({ issue: 'SHORT_SKU', sku });
    continue;
  }
  if (seen.has(sku)) {
    dqIssues.push({
      issue: 'DUPLICATE_SKU',
      sku,
      row_number: row.row_number ?? null,
      action: 'included',
    });
  }
  seen.add(sku);

  valid.push({
    sku,
    brand: row.UNIDADE ? String(row.UNIDADE).trim() : '',
    description: row.ITEM ? String(row.ITEM).trim() : '',
    row_number: row.row_number ?? null,
    notify_email: row['E-MAIL'] ? String(row['E-MAIL']).trim() : '',
    notify_phone: row.CONTATO ? String(row.CONTATO).trim() : '',
  });
}

const duplicateIssues = dqIssues.filter((i) => i.issue === 'DUPLICATE_SKU');
const duplicateSkus = [...new Set(duplicateIssues.map((i) => i.sku).filter(Boolean))];

return [
  {
    json: {
      total_read: raw.length,
      valid_skus: valid.length,
      unique_skus: seen.size,
      skipped_processado: skippedProcessado,
      duplicates: duplicateIssues.length,
      duplicate_skus: duplicateSkus,
      empty_skus: dqIssues.filter((i) => i.issue === 'EMPTY_SKU').length,
      short_skus: dqIssues.filter((i) => i.issue === 'SHORT_SKU').length,
      dq_issues: dqIssues,
      skus: valid,
      dispatched_at: new Date().toISOString(),
    },
  },
];
