#!/usr/bin/env bash
# Configure CDP_STOKAI_* environment on the shared n8n Container App.
set -euo pipefail

RG="${N8N_RESOURCE_GROUP:-automation}"
APP="${N8N_APP_NAME:-cdp-n8n-prod}"
STOKAI_RESOURCE_GROUP="${STOKAI_RESOURCE_GROUP:-stokai-tk}"
STOKAI_KEY_VAULT_NAME="${STOKAI_KEY_VAULT_NAME:-${KEY_VAULT_NAME:-cdp-stokai-kv-prod}}"
STOKAI_SCRAPER_APP_NAME="${STOKAI_SCRAPER_APP_NAME:-cdp-stokai-scrapers-api-prod}"
STOKAI_MUVSTOK_APP_NAME="${STOKAI_MUVSTOK_APP_NAME:-cdp-stokai-muv-api}"

require_env() {
  local name="$1"
  if [[ -z "${!name:-}" ]]; then
    echo "Missing required env: ${name}" >&2
    exit 1
  fi
}

kv_secret() {
  local name="$1"
  az keyvault secret show \
    --vault-name "${STOKAI_KEY_VAULT_NAME}" \
    --name "${name}" \
    --query value \
    -o tsv 2>/dev/null | tr -d '\r' || true
}

containerapp_url() {
  local app_name="$1"
  local fqdn
  fqdn="$(az containerapp show \
    --resource-group "${STOKAI_RESOURCE_GROUP}" \
    --name "${app_name}" \
    --query properties.configuration.ingress.fqdn \
    -o tsv 2>/dev/null | tr -d '\r\n' || true)"
  if [[ -n "${fqdn}" ]]; then
    printf 'https://%s' "${fqdn}"
  fi
}

CDP_STOKAI_SCRAPER_API_BASE="${CDP_STOKAI_SCRAPER_API_BASE:-$(containerapp_url "${STOKAI_SCRAPER_APP_NAME}")}"
CDP_STOKAI_MUVSTOK_API_BASE="${CDP_STOKAI_MUVSTOK_API_BASE:-$(containerapp_url "${STOKAI_MUVSTOK_APP_NAME}")}"

require_env CDP_STOKAI_SCRAPER_API_BASE
require_env CDP_STOKAI_MUVSTOK_API_BASE

CDP_STOKAI_API_KEY="${CDP_STOKAI_API_KEY:-$(kv_secret api-key)}"
CDP_STOKAI_MUVSTOK_API_KEY="${CDP_STOKAI_MUVSTOK_API_KEY:-${CDP_STOKAI_API_KEY}}"
CDP_STOKAI_CALLBACK_WEBHOOK_SECRET="${CDP_STOKAI_CALLBACK_WEBHOOK_SECRET:-$(kv_secret callback-webhook-secret)}"
CDP_STOKAI_MUVSTOK_CALLBACK_WEBHOOK_SECRET="${CDP_STOKAI_MUVSTOK_CALLBACK_WEBHOOK_SECRET:-${CDP_STOKAI_CALLBACK_WEBHOOK_SECRET}}"
CDP_STOKAI_WEBHOOK_URL="${CDP_STOKAI_WEBHOOK_URL:-https://automacao.tktechnologies.com.br/}"
CDP_STOKAI_N8N_WEBHOOK_PATH="${CDP_STOKAI_N8N_WEBHOOK_PATH:-webhook/stokai-scraper-result}"
CDP_STOKAI_MUVSTOK_WEBHOOK_PATH="${CDP_STOKAI_MUVSTOK_WEBHOOK_PATH:-webhook/stokai-muvstok-result}"
CDP_STOKAI_NOTIFIER_WEBHOOK_PATH="${CDP_STOKAI_NOTIFIER_WEBHOOK_PATH:-webhook/stokai-cdp-notifier}"
CDP_STOKAI_SCRAPER_SITES="${CDP_STOKAI_SCRAPER_SITES:-gm,ml,vw,eu,melibox}"
CDP_STOKAI_PROGRESS_INTERVAL_MIN="${CDP_STOKAI_PROGRESS_INTERVAL_MIN:-10}"
CDP_STOKAI_PROGRESS_MIN_SKUS="${CDP_STOKAI_PROGRESS_MIN_SKUS:-15}"
CDP_STOKAI_PROGRESS_MIN_STEP_PCT="${CDP_STOKAI_PROGRESS_MIN_STEP_PCT:-10}"
CDP_STOKAI_PROGRESS_MAX_MESSAGES="${CDP_STOKAI_PROGRESS_MAX_MESSAGES:-6}"
CDP_STOKAI_SCRAPER_BATCH_SIZE="${CDP_STOKAI_SCRAPER_BATCH_SIZE:-}"

SECRET_ARGS=()
if [[ -n "${CDP_STOKAI_API_KEY}" ]]; then
  SECRET_ARGS+=("cdp-stokai-api-key=${CDP_STOKAI_API_KEY}")
fi
if [[ -n "${CDP_STOKAI_MUVSTOK_API_KEY}" ]]; then
  SECRET_ARGS+=("cdp-stokai-muvstok-api-key=${CDP_STOKAI_MUVSTOK_API_KEY}")
fi
if [[ -n "${CDP_STOKAI_CALLBACK_WEBHOOK_SECRET}" ]]; then
  SECRET_ARGS+=("cdp-stokai-callback-webhook-secret=${CDP_STOKAI_CALLBACK_WEBHOOK_SECRET}")
fi
if [[ -n "${CDP_STOKAI_MUVSTOK_CALLBACK_WEBHOOK_SECRET}" ]]; then
  SECRET_ARGS+=("cdp-stokai-muvstok-callback-webhook-secret=${CDP_STOKAI_MUVSTOK_CALLBACK_WEBHOOK_SECRET}")
fi

if (( ${#SECRET_ARGS[@]} > 0 )); then
  echo "==> Patch STOKAI secrets on ${APP} (${RG})"
  az containerapp secret set -g "${RG}" -n "${APP}" --secrets "${SECRET_ARGS[@]}" --output none
fi

ENV_ARGS=(
  "CDP_ENV=shared"
  "CDP_STOKAI_SCRAPER_API_BASE=${CDP_STOKAI_SCRAPER_API_BASE}"
  "CDP_STOKAI_MUVSTOK_API_BASE=${CDP_STOKAI_MUVSTOK_API_BASE}"
  "CDP_STOKAI_WEBHOOK_URL=${CDP_STOKAI_WEBHOOK_URL}"
  "CDP_STOKAI_N8N_WEBHOOK_PATH=${CDP_STOKAI_N8N_WEBHOOK_PATH}"
  "CDP_STOKAI_MUVSTOK_WEBHOOK_PATH=${CDP_STOKAI_MUVSTOK_WEBHOOK_PATH}"
  "CDP_STOKAI_NOTIFIER_WEBHOOK_PATH=${CDP_STOKAI_NOTIFIER_WEBHOOK_PATH}"
  "CDP_STOKAI_SCRAPER_SITES=${CDP_STOKAI_SCRAPER_SITES}"
  "CDP_STOKAI_PROGRESS_INTERVAL_MIN=${CDP_STOKAI_PROGRESS_INTERVAL_MIN}"
  "CDP_STOKAI_PROGRESS_MIN_SKUS=${CDP_STOKAI_PROGRESS_MIN_SKUS}"
  "CDP_STOKAI_PROGRESS_MIN_STEP_PCT=${CDP_STOKAI_PROGRESS_MIN_STEP_PCT}"
  "CDP_STOKAI_PROGRESS_MAX_MESSAGES=${CDP_STOKAI_PROGRESS_MAX_MESSAGES}"
)

if [[ -n "${CDP_STOKAI_SCRAPER_BATCH_SIZE}" ]]; then
  ENV_ARGS+=("CDP_STOKAI_SCRAPER_BATCH_SIZE=${CDP_STOKAI_SCRAPER_BATCH_SIZE}")
fi
if [[ -n "${CDP_STOKAI_API_KEY}" ]]; then
  ENV_ARGS+=("CDP_STOKAI_API_KEY=secretref:cdp-stokai-api-key")
fi
if [[ -n "${CDP_STOKAI_MUVSTOK_API_KEY}" ]]; then
  ENV_ARGS+=("CDP_STOKAI_MUVSTOK_API_KEY=secretref:cdp-stokai-muvstok-api-key")
fi
if [[ -n "${CDP_STOKAI_CALLBACK_WEBHOOK_SECRET}" ]]; then
  ENV_ARGS+=("CDP_STOKAI_CALLBACK_WEBHOOK_SECRET=secretref:cdp-stokai-callback-webhook-secret")
fi
if [[ -n "${CDP_STOKAI_MUVSTOK_CALLBACK_WEBHOOK_SECRET}" ]]; then
  ENV_ARGS+=("CDP_STOKAI_MUVSTOK_CALLBACK_WEBHOOK_SECRET=secretref:cdp-stokai-muvstok-callback-webhook-secret")
fi

echo "==> Update STOKAI env vars on ${APP}"
az containerapp update -g "${RG}" -n "${APP}" --set-env-vars "${ENV_ARGS[@]}" --output none

echo "Configured shared n8n STOKAI environment on ${APP}"
