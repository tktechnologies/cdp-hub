#!/usr/bin/env bash
# Smoke-test Redis scrape cache on localhost (API + Redis required).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

API_BASE="${API_BASE:-http://localhost:8000/api/v1}"
API_KEY="${API_KEY:-dev-key-change-in-production}"
API_BASE="${API_BASE//$'\r'/}"
API_BASE="${API_BASE//$'\n'/}"
API_KEY="${API_KEY//$'\r'/}"
API_KEY="${API_KEY//$'\n'/}"
SKU="${SKU:-93338835}"
BRAND="${BRAND:-GM}"
SITES_JSON="${SITES_JSON:-[\"gm\"]}"
REDIS_URL="${SCRAPE_CACHE_REDIS_URL:-redis://localhost:6379/1}"

echo "=== Scrape cache local smoke ==="
echo "API: ${API_BASE}"
echo "SKU: ${SKU} brand=${BRAND} sites=${SITES_JSON}"
echo "Cache Redis: ${REDIS_URL}"

if command -v redis-cli >/dev/null 2>&1; then
  if ! redis-cli -u "${REDIS_URL}" ping >/dev/null 2>&1; then
    echo "ERROR: Redis not reachable at ${REDIS_URL}"
    echo "Start with: docker compose up -d redis"
    exit 1
  fi
  echo "Redis: PONG"
else
  echo "WARN: redis-cli not found; skipping Redis ping"
fi

if ! curl -sf "${API_BASE%/api/v1}/api/v1/health" -o /dev/null 2>/dev/null; then
  if ! curl -sf "http://localhost:8000/api/v1/health" -o /dev/null; then
    echo "ERROR: API not reachable. Start with: make dev"
    exit 1
  fi
  API_BASE="http://localhost:8000/api/v1"
fi
echo "API health: OK"

lookup() {
  local label="$1"
  local force="$2"
  echo ""
  echo "--- ${label} (force_refresh=${force}) ---"
  curl -s -X POST "${API_BASE}/lookup" \
    -H "X-API-Key: ${API_KEY}" \
    -H "Content-Type: application/json" \
    -d "{\"sku\":\"${SKU}\",\"brand\":\"${BRAND}\",\"sites\":${SITES_JSON},\"force_refresh\":${force}}" \
    | tee "/tmp/scrape_cache_${label}.json" \
    | python3 -c "
import json, sys
d = json.load(sys.stdin)
sr = (d.get('site_results') or [{}])[0]
print('cache_hits:', d.get('cache_hits'))
print('live_scrapes:', d.get('live_scrapes'))
print('from_cache:', sr.get('from_cache'))
print('status:', sr.get('status'))
print('cached_at:', sr.get('cached_at'))
"
}

lookup "first_live" "true"
lookup "second_cached" "false"
lookup "third_force" "true"

echo ""
echo "PASS criteria for second call: cache_hits>=1, live_scrapes=0, from_cache=true"
second="$(python3 -c "import json; d=json.load(open('/tmp/scrape_cache_second_cached.json')); print(d.get('cache_hits',0), d.get('live_scrapes',-1), (d.get('site_results') or [{}])[0].get('from_cache'))")"
read -r hits live cached <<< "${second}"
if [[ "${hits}" -ge 1 && "${live}" == "0" && "${cached}" == "True" ]]; then
  echo "=== LOCAL CACHE SMOKE: PASS ==="
  exit 0
fi
echo "=== LOCAL CACHE SMOKE: FAIL (got hits=${hits} live=${live} cached=${cached}) ==="
exit 1
