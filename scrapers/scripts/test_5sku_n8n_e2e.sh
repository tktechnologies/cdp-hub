#!/usr/bin/env bash
# E2E: 5 random SKUs from production pool -> POST /jobs -> poll -> callback n8n
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
API_FQDN="$(az containerapp show -g automation -n cdp-scrapers-api-prod \
  --query properties.configuration.ingress.fqdn -o tsv | tr -d '\r\n')"
API_KEY="$(az keyvault secret show --vault-name cdp-scrapers-kv-prod \
  --name api-key --query value -o tsv | tr -d '\r\n')"
API_BASE="https://${API_FQDN}/api/v1"
CALLBACK="https://automacao.tktechnologies.com.br/webhook/scraper-result?source=5sku-e2e&notify=none"
OUT="${1:-/tmp/5sku_e2e_job.json}"
SEED="${PRODUCTION_TEST_SKU_SEED:-}"

BODY="$(UV_CACHE_DIR=/tmp/uv-cache uv run python -c "
import json, os, sys
sys.path.insert(0, '${ROOT}/scripts')
from production_sku_pool import resolve_seed, sample_batch_job_items
seed = os.environ.get('PRODUCTION_TEST_SKU_SEED') or None
seed = int(seed) if seed else None
items, sites, cases = sample_batch_job_items(5, seed=seed, sites=('gm', 'pecadireta', 'melibox'))
print(json.dumps({
    'items': items,
    'sites': sites,
    'callback_url': '${CALLBACK}',
    'force_refresh': False,
    'priority': 5,
    '_meta': {'seed': resolve_seed(seed), 'cases': cases},
}, ensure_ascii=False))
")"

echo "=== Sampled SKUs ==="
echo "$BODY" | python3 -c "import json,sys; d=json.load(sys.stdin); m=d.pop('_meta',{}); print('seed', m.get('seed'), file=sys.stderr);
[print(' ', c['sku'], c.get('brand',''), file=sys.stderr) for c in m.get('cases',[])]; json.dump(d, sys.stdout)" > /tmp/5sku_job_body.json
BODY="$(cat /tmp/5sku_job_body.json)"

echo "=== Health ==="
curl -sf "${API_BASE}/health"
echo ""

echo "=== Submit job (5 SKUs) ==="
SUBMIT=$(curl -sf -X POST "${API_BASE}/jobs" \
  -H "X-API-Key: ${API_KEY}" -H "Content-Type: application/json" \
  -d "$BODY")
echo "$SUBMIT" | python3 -m json.tool
JOB_ID=$(echo "$SUBMIT" | python3 -c "import json,sys; print(json.load(sys.stdin)['job_id'])")
echo "JOB_ID=$JOB_ID"

echo "=== Poll (max 300s) ==="
for i in $(seq 1 60); do
  POLL=$(curl -sf "${API_BASE}/jobs/${JOB_ID}" -H "X-API-Key: ${API_KEY}")
  STATUS=$(echo "$POLL" | python3 -c "import json,sys; print(json.load(sys.stdin).get('status',''))")
  echo "  [$i] status=$STATUS"
  if [[ "$STATUS" == "completed" || "$STATUS" == "partial" || "$STATUS" == "failed" ]]; then
    echo "$POLL" | python3 -c "
import json, sys
p = json.load(sys.stdin)
out = {
  'job_id': p.get('job_id'),
  'status': p.get('status'),
  'duration_seconds': p.get('duration_seconds'),
  'items_succeeded': p.get('items_succeeded'),
  'items_failed': p.get('items_failed'),
  'results': [{
    'sku': r.get('sku'),
    'brand': r.get('brand'),
    'cache_hits': r.get('cache_hits'),
    'live_scrapes': r.get('live_scrapes'),
    'best_price': (r.get('best_price') or {}) and {
      'price': r['best_price'].get('price'),
      'currency': r['best_price'].get('currency'),
      'exact_match': r['best_price'].get('exact_match'),
    },
    'sites': [{'site': s.get('site'), 'status': s.get('status'), 'from_cache': s.get('from_cache'),
               'results_count': len(s.get('results') or [])} for s in (r.get('site_results') or [])],
  } for r in (p.get('results') or [])],
}
json.dump(out, open('${OUT}', 'w'), indent=2)
print(json.dumps(out, indent=2))
"
    exit 0
  fi
  sleep 5
done
echo "TIMEOUT waiting for job $JOB_ID" >&2
exit 1
