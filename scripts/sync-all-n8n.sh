#!/usr/bin/env bash
# Sync shared router JS → local JSON → n8n MCP (validate, update, publish).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "==> Inject n8n/src into cdp_router.json"
python3 scripts/sync_workflow_code_from_shared.py

if [[ -f scrapers/scripts/patch_scraper_receiver_workflow.py ]]; then
  echo "==> Patch cdp_scraper receiver (Telegram lib, NOTIFICADO ad_hoc)"
  python3 scrapers/scripts/patch_scraper_receiver_workflow.py
fi

if [[ -f muvstok-api/scripts/patch_muvstok_receiver_workflow.py ]]; then
  echo "==> Patch cdp_stokapi receiver (Telegram lib, sheets)"
  python3 muvstok-api/scripts/patch_muvstok_receiver_workflow.py
fi

mkdir -p n8n/sdk

echo "==> Generate SDK: cdp_router"
node scrapers/scripts/n8n_workflow_json_to_sdk.mjs \
  n8n/workflows/cdp_router.json \
  --workflow-id=6id6dkinK9xTLfsb \
  --workflow-name=cdp_router \
  > n8n/sdk/cdp_router.workflow.ts

echo "==> Generate SDK: cdp_scraper"
node scrapers/scripts/n8n_workflow_json_to_sdk.mjs \
  n8n/workflows/cdp_scraper.json \
  --workflow-id=VfBSV3WU6on8BXm8 \
  --workflow-name=cdp_scraper \
  > n8n/sdk/cdp_scraper.workflow.ts

echo "==> Generate SDK: cdp_stokapi"
node scrapers/scripts/n8n_workflow_json_to_sdk.mjs \
  n8n/workflows/cdp_stokapi.json \
  --workflow-id=t160mzGPYYlJcrjZ \
  --workflow-name=cdp_stokapi \
  > n8n/sdk/cdp_stokapi.workflow.ts

echo "==> Push cdp_router"
python3 scrapers/scripts/push_workflow_mcp.py \
  --workflow-id=6id6dkinK9xTLfsb \
  --sdk=n8n/sdk/cdp_router.workflow.ts \
  --description="CDP router: .analisar/.sku → Scraper + StokAPI" \
  --publish

echo "==> Push cdp_scraper"
python3 scrapers/scripts/push_workflow_mcp.py \
  --workflow-id=VfBSV3WU6on8BXm8 \
  --sdk=n8n/sdk/cdp_scraper.workflow.ts \
  --description="CDP scraper receiver: webhook scraper-result" \
  --publish

echo "==> Push cdp_stokapi"
python3 scrapers/scripts/push_workflow_mcp.py \
  --workflow-id=t160mzGPYYlJcrjZ \
  --sdk=n8n/sdk/cdp_stokapi.workflow.ts \
  --description="CDP StokAPI receiver: webhook muvstok-result" \
  --publish

echo "==> Done. Optional: archive legacy starter PXLHDzRbBVgs8Xl2 in n8n UI if still active."
