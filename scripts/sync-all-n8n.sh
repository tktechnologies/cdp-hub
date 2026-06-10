#!/usr/bin/env bash
# Sync shared router JS → local JSON → n8n REST API push → MCP publish.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
N8N_TARGET="${N8N_TARGET:-prod}"

case "$N8N_TARGET" in
  prod|dev) ;;
  *)
    echo "N8N_TARGET must be prod or dev (got: ${N8N_TARGET})" >&2
    exit 1
    ;;
esac

require_env() {
  local name="$1"
  if [[ -z "${!name:-}" ]]; then
    echo "Missing required env for N8N_TARGET=${N8N_TARGET}: ${name}" >&2
    exit 1
  fi
}

echo "==> Inject n8n/src into cdp_router.json (+ cdp_progress.json)"
python3 scripts/sync_workflow_code_from_shared.py

echo "==> Build cdp_notifier workflow JSON"
python3 scripts/build_cdp_notifier_workflow.py

echo "==> Patch cdp_notifier (CSV attachment + send guards)"
python3 scripts/patch_cdp_notifier_workflow.py

echo "==> Patch cdp_skus sheet tab refs (+ notifier NOTIFICADO writeback)"
python3 scripts/patch_cdp_skus_sheet_nodes.py

echo "==> Patch receivers for aggregate notifier handoff"
python3 scripts/patch_receiver_notifier_handoff.py

if [[ -f scrapers/scripts/patch_scraper_receiver_workflow.py ]]; then
  echo "==> Patch cdp_scraper receiver (Telegram lib, NOTIFICADO ad_hoc)"
  python3 scrapers/scripts/patch_scraper_receiver_workflow.py
fi

if [[ -f muvstok-api/scripts/patch_muvstok_receiver_workflow.py ]]; then
  echo "==> Patch cdp_stokapi receiver (Telegram lib, sheets)"
  python3 muvstok-api/scripts/patch_muvstok_receiver_workflow.py
fi

if [[ "$N8N_TARGET" == "dev" ]]; then
  echo "==> Generate DEV workflow copies in shared n8n model"
  python3 scripts/generate_dev_n8n_workflows.py --require-telegram-credential
fi

mkdir -p n8n/sdk

gen_sdk() {
  local json="$1" id="$2" name="$3" out="$4"
  echo "==> Generate SDK: ${name}"
  node scrapers/scripts/n8n_workflow_json_to_sdk.mjs \
    "$json" --workflow-id="$id" --workflow-name="$name" > "$out"
}

if [[ "$N8N_TARGET" == "prod" ]]; then
  ROUTER_ID="6id6dkinK9xTLfsb"
  SCRAPER_ID="VfBSV3WU6on8BXm8"
  STOKAPI_ID="t160mzGPYYlJcrjZ"
  PROGRESS_ID="${CDP_PROGRESS_WORKFLOW_ID:-}"

  ROUTER_JSON="n8n/workflows/cdp_router.json"
  SCRAPER_JSON="n8n/workflows/cdp_scraper.json"
  STOKAPI_JSON="n8n/workflows/cdp_stokapi.json"
  PROGRESS_JSON="n8n/workflows/cdp_progress.json"

  ROUTER_NAME="cdp_router"
  SCRAPER_NAME="cdp_scraper"
  STOKAPI_NAME="cdp_stokapi"
  PROGRESS_NAME="cdp_progress"

  ROUTER_SDK="n8n/sdk/cdp_router.workflow.ts"
  SCRAPER_SDK="n8n/sdk/cdp_scraper.workflow.ts"
  STOKAPI_SDK="n8n/sdk/cdp_stokapi.workflow.ts"
  PROGRESS_SDK="n8n/sdk/cdp_progress.workflow.ts"

  ROUTER_DESC="CDP router: .analisar/.sku -> Scraper + StokAPI"
  SCRAPER_DESC="CDP scraper receiver: webhook scraper-result"
  STOKAPI_DESC="CDP StokAPI receiver: webhook muvstok-result"
  PROGRESS_DESC="CDP progress: proactive Telegram while dual runs active"
  NOTIFIER_ID="${CDP_NOTIFIER_WORKFLOW_ID:-}"
  NOTIFIER_JSON="n8n/workflows/cdp_notifier.json"
  NOTIFIER_NAME="cdp_notifier"
  NOTIFIER_SDK="n8n/sdk/cdp_notifier.workflow.ts"
  NOTIFIER_DESC="CDP notifier: single final message after dual pipeline"
else
  require_env CDP_DEV_ROUTER_WORKFLOW_ID
  require_env CDP_DEV_SCRAPER_WORKFLOW_ID
  require_env CDP_DEV_STOKAPI_WORKFLOW_ID
  require_env CDP_DEV_PROGRESS_WORKFLOW_ID

  ROUTER_ID="${CDP_DEV_ROUTER_WORKFLOW_ID}"
  SCRAPER_ID="${CDP_DEV_SCRAPER_WORKFLOW_ID}"
  STOKAPI_ID="${CDP_DEV_STOKAPI_WORKFLOW_ID}"
  PROGRESS_ID="${CDP_DEV_PROGRESS_WORKFLOW_ID}"

  ROUTER_JSON="n8n/workflows/dev/dev_cdp_router.json"
  SCRAPER_JSON="n8n/workflows/dev/dev_cdp_scraper.json"
  STOKAPI_JSON="n8n/workflows/dev/dev_cdp_stokapi.json"
  PROGRESS_JSON="n8n/workflows/dev/dev_cdp_progress.json"

  ROUTER_NAME="DEV - cdp_router"
  SCRAPER_NAME="DEV - cdp_scraper"
  STOKAPI_NAME="DEV - cdp_stokapi"
  PROGRESS_NAME="DEV - cdp_progress"

  ROUTER_SDK="n8n/sdk/dev_cdp_router.workflow.ts"
  SCRAPER_SDK="n8n/sdk/dev_cdp_scraper.workflow.ts"
  STOKAPI_SDK="n8n/sdk/dev_cdp_stokapi.workflow.ts"
  PROGRESS_SDK="n8n/sdk/dev_cdp_progress.workflow.ts"

  ROUTER_DESC="DEV CDP router: Telegram DEV bot -> DEV Scraper + DEV StokAPI"
  SCRAPER_DESC="DEV CDP scraper receiver: webhook dev-scraper-result"
  STOKAPI_DESC="DEV CDP StokAPI receiver: webhook dev-muvstok-result"
  PROGRESS_DESC="DEV CDP progress: proactive Telegram while DEV runs active"
  NOTIFIER_ID="${CDP_DEV_NOTIFIER_WORKFLOW_ID:-}"
  NOTIFIER_JSON="n8n/workflows/dev/dev_cdp_notifier.json"
  NOTIFIER_NAME="DEV - cdp_notifier"
  NOTIFIER_SDK="n8n/sdk/dev_cdp_notifier.workflow.ts"
  NOTIFIER_DESC="DEV CDP notifier: single final message after dual pipeline"
fi

gen_sdk "$ROUTER_JSON" "$ROUTER_ID" "$ROUTER_NAME" "$ROUTER_SDK"
gen_sdk "$SCRAPER_JSON" "$SCRAPER_ID" "$SCRAPER_NAME" "$SCRAPER_SDK"
gen_sdk "$STOKAPI_JSON" "$STOKAPI_ID" "$STOKAPI_NAME" "$STOKAPI_SDK"
gen_sdk "$PROGRESS_JSON" "${PROGRESS_ID:-progress-local}" "$PROGRESS_NAME" "$PROGRESS_SDK"

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

push_wf "$ROUTER_ID" "$ROUTER_JSON" "$ROUTER_SDK" "$ROUTER_DESC"
push_wf "$SCRAPER_ID" "$SCRAPER_JSON" "$SCRAPER_SDK" "$SCRAPER_DESC"
push_wf "$STOKAPI_ID" "$STOKAPI_JSON" "$STOKAPI_SDK" "$STOKAPI_DESC"

if [[ -n "${PROGRESS_ID:-}" ]]; then
  push_wf "$PROGRESS_ID" "$PROGRESS_JSON" "$PROGRESS_SDK" "$PROGRESS_DESC"
else
  echo "==> Skip cdp_progress push (set CDP_PROGRESS_WORKFLOW_ID after first n8n import)"
fi

if [[ -n "${NOTIFIER_ID:-}" ]]; then
  gen_sdk "$NOTIFIER_JSON" "$NOTIFIER_ID" "$NOTIFIER_NAME" "$NOTIFIER_SDK"
  push_wf "$NOTIFIER_ID" "$NOTIFIER_JSON" "$NOTIFIER_SDK" "$NOTIFIER_DESC"
else
  echo "==> Skip cdp_notifier push (import cdp_notifier.json once, set CDP_NOTIFIER_WORKFLOW_ID)"
fi

echo "==> Done (${N8N_TARGET})."
