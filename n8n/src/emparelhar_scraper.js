// cdp_router — pair scraper HTTP responses to SKUs for sheet PROCESSADO updates.

const httpItems = $input.all();
const batches = $('⚙️ Formatar Payload Scraper').all();
const out = [];
for (let i = 0; i < httpItems.length; i++) {
  const resp = httpItems[i].json;
  const hasJob = Boolean(resp.job_id);
  const sc = resp.statusCode != null ? Number(resp.statusCode) : hasJob ? 200 : 0;
  if (!hasJob && (sc < 200 || sc >= 300)) continue;
  const batch = batches[i]?.json;
  if (!batch) continue;
  for (const it of batch.items || []) {
    if (it && it.sku) out.push({ json: { sku: String(it.sku).trim() } });
  }
}
return out;
