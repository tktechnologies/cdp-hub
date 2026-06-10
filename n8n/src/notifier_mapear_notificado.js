// cdp_notifier — merge NOTIFICADO status onto sheet rows (preserve row_number lineage).

const trigger = $('🔧 Expandir NOTIFICADO').first().json || {};
const status = trigger.NOTIFICADO || '✅ Notificado';
const marksByRow = {};
for (const rn of trigger.sheet_row_numbers || []) {
  const n = Number(rn);
  if (Number.isFinite(n) && n > 0) marksByRow[n] = status;
}

const items = $input.all();
const out = [];
for (let i = 0; i < items.length; i++) {
  const item = items[i];
  const row = item.json || {};
  const rn = row.row_number;
  if (marksByRow[rn] === undefined) continue;
  out.push({
    json: {
      ...row,
      NOTIFICADO: marksByRow[rn],
    },
    pairedItem: item.pairedItem ?? { item: i },
  });
}
return out;
