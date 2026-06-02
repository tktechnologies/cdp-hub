#!/usr/bin/env bash
# Sync shared router JS → local JSON → n8n REST API push → MCP publish.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "==> Inject n8n/src into cdp_router.json (+ cdp_progress.json)"
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

gen_sdk() {
  local json="$1" id="$2" name="$3" out="$4"
  echo "==> Generate SDK: ${name}"
  node scrapers/scripts/n8n_workflow_json_to_sdk.mjs \
    "$json" --workflow-id="$id" --workflow-name="$name" > "$out"
}

gen_sdk n8n/workflows/cdp_router.json 6id6dkinK9xTLfsb cdp_router n8n/sdk/cdp_router.workflow.ts
gen_sdk n8n/workflows/cdp_scraper.json VfBSV3WU6on8BXm8 cdp_scraper n8n/sdk/cdp_scraper.workflow.ts
gen_sdk n8n/workflows/cdp_stokapi.json t160mzGPYYlJcrjZ cdp_stokapi n8n/sdk/cdp_stokapi.workflow.ts
gen_sdk n8n/workflows/cdp_progress.json progress-local cdp_progress n8n/sdk/cdp_progress.workflow.ts

push_wf() {
  local id="$1" json="$2" sdk="$3" desc="$4"
  echo "==> Push ${json##*/}"
  python3 scripts/n8n_publish.py \
    --workflow-id="$id" \
    --json="$json" \
    --sdk="$sdk" \
    --description="$desc" \
    --publish
}

push_wf 6id6dkinK9xTLfsb n8n/workflows/cdp_router.json n8n/sdk/cdp_router.workflow.ts \
  "CDP router: .analisar/.sku → Scraper + StokAPI"
push_wf VfBSV3WU6on8BXm8 n8n/workflows/cdp_scraper.json n8n/sdk/cdp_scraper.workflow.ts \
  "CDP scraper receiver: webhook scraper-result"
push_wf t160mzGPYYlJcrjZ n8n/workflows/cdp_stokapi.json n8n/sdk/cdp_stokapi.workflow.ts \
  "CDP StokAPI receiver: webhook muvstok-result"

if [[ -n "${CDP_PROGRESS_WORKFLOW_ID:-}" ]]; then
  push_wf "$CDP_PROGRESS_WORKFLOW_ID" n8n/workflows/cdp_progress.json n8n/sdk/cdp_progress.workflow.ts \
    "CDP progress: proactive Telegram while dual runs active"
else
  echo "==> Skip cdp_progress push (set CDP_PROGRESS_WORKFLOW_ID after first n8n import)"
fi

echo "==> Done."
