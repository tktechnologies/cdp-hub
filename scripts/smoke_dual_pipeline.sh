#!/usr/bin/env bash
# Smoke test: scraper cache + job API (no Telegram). Requires API_KEY and reachable APIs.
set -euo pipefail

SCRAPER_BASE="${CDP_SCRAPER_API_BASE:-https://cdp-scrapers-api-prod.bravecoast-b14d791e.eastus2.azurecontainerapps.io}"
MUV_BASE="${CDP_MUVSTOK_API_BASE:-https://cdp-muv-api.bravecoast-b14d791e.eastus2.azurecontainerapps.io}"
API_KEY="${CDP_API_KEY:-${API_KEY:-}}"
SKU="${SMOKE_SKU:-7703062062}"
WEBHOOK="${WEBHOOK_URL:-https://automacao.tktechnologies.com.br}"

if [[ -z "$API_KEY" ]]; then
  echo "Set CDP_API_KEY or API_KEY" >&2
  exit 1
fi

echo "==> Scraper health"
curl -fsS "$SCRAPER_BASE/api/v1/health" | head -c 200
echo

echo "==> Lookup (cache-aware) run 1"
curl -fsS -X POST "$SCRAPER_BASE/api/v1/lookup" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d "{\"sku\":\"$SKU\",\"sites\":[\"gm\"]}" | python3 -c "
import json,sys
d=json.load(sys.stdin)
sr=d.get('site_results') or d.get('results') or []
for r in sr[:3]:
  print('  site', r.get('site'), 'status', r.get('status'), 'from_cache', r.get('from_cache'), 'live', r.get('live_scrapes', '?'))
"

echo "==> Lookup run 2 (expect from_cache on Redis hit)"
curl -fsS -X POST "$SCRAPER_BASE/api/v1/lookup" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d "{\"sku\":\"$SKU\",\"sites\":[\"gm\"]}" | python3 -c "
import json,sys
d=json.load(sys.stdin)
hits=sum(1 for r in (d.get('site_results') or []) if r.get('from_cache'))
print('  cache_hits', hits, '/', len(d.get('site_results') or []))
"

echo "==> Muvstok health"
curl -fsS "$MUV_BASE/api/v1/muvstok/health" | head -c 200
echo

echo "==> OK (manual: send .sku $SKU on Telegram to test full n8n path)"
