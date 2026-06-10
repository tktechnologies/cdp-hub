// cdp_notifier — trigger sheet NOTIFICADO updates (row numbers from final formatter).

const prep = $('📣 Formatar mensagem final').first().json;
const rows = Array.isArray(prep.sheet_row_numbers) ? prep.sheet_row_numbers : [];
const status = prep.skipped_no_target ? '🚫 Sem destino' : '✅ Notificado';

if (!rows.length) {
  return [];
}

return [
  {
    json: {
      sheet_row_numbers: rows
        .map((rowNumber) => Number(rowNumber))
        .filter((n) => Number.isFinite(n) && n > 0),
      NOTIFICADO: status,
    },
  },
];
