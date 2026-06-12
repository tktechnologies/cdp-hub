// cdp_router — validate sheet rows, dedupe dispatch SKUs, preserve sheet rows.

const rawItems = $input.all();
const seen = new Set();
const uniqueBySku = new Map();
const sheetRows = [];
const dqIssues = [];
let skippedProcessado = 0;

function hasMeaningfulValue(row) {
  if (!row || typeof row !== 'object') return false;
  return Object.entries(row).some(([key, value]) => {
    if (key === 'row_number') return false;
    if (value === null || value === undefined) return false;
    return String(value).trim() !== '';
  });
}

function normalizeStatus(value) {
  return String(value || '')
    .trim()
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9]+/g, ' ')
    .trim();
}

function normalizeSku(value) {
  return String(value || '')
    .trim()
    .toUpperCase()
    .replace(/[\s\-\.\\/]/g, '');
}

function pickSheetField(row, base) {
  if (!row || typeof row !== 'object') return '';
  const robot = base + ' 🤖';
  for (const k of [base, robot]) {
    const v = row[k];
    if (v !== null && v !== undefined && String(v).trim() !== '') return v;
  }
  return row[base] ?? row[robot] ?? '';
}

const raw = rawItems.filter((item) => hasMeaningfulValue(item.json));

for (const item of raw) {
  const row = item.json;
  const rawSku = row.CODIGO ?? row.SKU ?? row.sku ?? row.codigo;
  const sku = normalizeSku(rawSku);

  const processado = normalizeStatus(pickSheetField(row, 'PROCESSADO'));
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
      action: 'deduped_dispatch_preserved_sheet_row',
    });
  }
  seen.add(sku);

  const rowData = {
    sku,
    sku_original: rawSku ? String(rawSku).trim() : '',
    brand: row.UNIDADE ? String(row.UNIDADE).trim() : '',
    description: row.ITEM ? String(row.ITEM).trim() : '',
    row_number: row.row_number ?? null,
    notify_email: row['E-MAIL'] ? String(row['E-MAIL']).trim() : '',
    notify_phone: row.CONTATO ? String(row.CONTATO).trim() : '',
  };
  sheetRows.push(rowData);

  if (!uniqueBySku.has(sku)) {
    uniqueBySku.set(sku, { ...rowData });
  } else {
    const existing = uniqueBySku.get(sku);
    if (existing) {
      if (!existing.brand && rowData.brand) existing.brand = rowData.brand;
      if (!existing.description && rowData.description) existing.description = rowData.description;
      if (!existing.notify_email && rowData.notify_email) existing.notify_email = rowData.notify_email;
      if (!existing.notify_phone && rowData.notify_phone) existing.notify_phone = rowData.notify_phone;
    }
  }
}

const duplicateIssues = dqIssues.filter((i) => i.issue === 'DUPLICATE_SKU');
const duplicateSkus = [...new Set(duplicateIssues.map((i) => i.sku).filter(Boolean))];
const skus = [...uniqueBySku.values()];

return [
  {
    json: {
      total_read: raw.length,
      input_valid_skus: sheetRows.length,
      valid_skus: skus.length,
      unique_skus: seen.size,
      skipped_processado: skippedProcessado,
      duplicates: duplicateIssues.length,
      duplicate_skus: duplicateSkus,
      empty_skus: dqIssues.filter((i) => i.issue === 'EMPTY_SKU').length,
      short_skus: dqIssues.filter((i) => i.issue === 'SHORT_SKU').length,
      dq_issues: dqIssues,
      skus,
      sheet_rows: sheetRows,
      dispatched_at: new Date().toISOString(),
    },
  },
];
