#!/usr/bin/env bash
# Smoke-test scrape cache on Azure production API (requires API_KEY).
set -euo pipefail

API_BASE="${API_BASE:-}"
API_KEY="${API_KEY:-}"
# Strip CR/LF from az CLI / Key Vault output (common source of 401 Invalid API key).
API_BASE="${API_BASE//$'\r'/}"
API_BASE="${API_BASE//$'\n'/}"
API_KEY="${API_KEY//$'\r'/}"
API_KEY="${API_KEY//$'\n'/}"
SKU="${SKU:-22781768}"
BRAND="${BRAND:-GM}"
SITES_JSON="${SITES_JSON:-[\"gm\"]}"

if [[ -z "${API_BASE}" || -z "${API_KEY}" ]]; then
  echo "Usage: API_BASE=https://<api-fqdn>/api/v1 API_KEY=<secret> $0"
  echo "Optional: SKU=... BRAND=... SITES_JSON='[\"gm\",\"ml\"]'"
  exit 1
fi

echo "=== Scrape cache production smoke ==="
echo "API: ${API_BASE}"

curl -sf "${API_BASE}/health" | python3 -c "import json,sys; print('health:', json.load(sys.stdin).get('status'))"

lookup() {
  local label="$1"
  local force="$2"
  echo ""
  echo "--- ${label} (force_refresh=${force}) ---"
  curl -s -X POST "${API_BASE}/lookup" \
    -H "X-API-Key: ${API_KEY}" \
    -H "Content-Type: application/json" \
    -d "{\"sku\":\"${SKU}\",\"brand\":\"${BRAND}\",\"sites\":${SITES_JSON},\"force_refresh\":${force}}" \
    | tee "/tmp/scrape_cache_prod_${label}.json" \
    | python3 -c "
import json, sys
d = json.load(sys.stdin)
for sr in d.get('site_results') or []:
    print(f\"  {sr.get('site')}: status={sr.get('status')} from_cache={sr.get('from_cache')} cached_at={sr.get('cached_at')}\")
print('cache_hits:', d.get('cache_hits'), 'live_scrapes:', d.get('live_scrapes'))
"
}

lookup "first_live" "true"
lookup "second_cached" "false"

second="$(python3 -c "import json; d=json.load(open('/tmp/scrape_cache_prod_second_cached.json')); print(d.get('cache_hits',0), d.get('live_scrapes',-1), any((sr or {}).get('from_cache') for sr in (d.get('site_results') or [])))")"
read -r hits live cached <<< "${second}"
if [[ "${hits}" -ge 1 && "${live}" == "0" && "${cached}" == "True" ]]; then
  echo "=== PRODUCTION CACHE SMOKE: PASS ==="
  exit 0
fi
echo "=== PRODUCTION CACHE SMOKE: FAIL (hits=${hits} live=${live} cached=${cached}) ==="
echo "Full JSON: /tmp/scrape_cache_prod_second_cached.json"
exit 1
