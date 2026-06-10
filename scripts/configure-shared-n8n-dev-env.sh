#!/usr/bin/env bash
# Configure CDP_DEV_* environment on the shared n8n Container App (cdp-n8n-prod).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RG="${RESOURCE_GROUP:-automation}"
APP="${N8N_APP_NAME:-cdp-n8n-prod}"

require_env() {
  local name="$1"
  if [[ -z "${!name:-}" ]]; then
    echo "Missing required env: ${name}" >&2
    exit 1
  fi
}

# Required for DEV Telegram + API routing on shared n8n.
require_env TELEGRAM_DEV_ALLOWED_CHAT_IDS
require_env TELEGRAM_DEV_BOT_TOKEN
require_env CDP_DEV_SCRAPER_API_BASE
require_env CDP_DEV_SKUS_SHEET_ID
require_env CDP_DEV_RESULTADOS_SHEET_ID

CDP_DEV_MUVSTOK_API_BASE="${CDP_DEV_MUVSTOK_API_BASE:-}"
CDP_DEV_API_KEY="${CDP_DEV_API_KEY:-}"
CDP_DEV_MUVSTOK_API_KEY="${CDP_DEV_MUVSTOK_API_KEY:-}"
CDP_DEV_CALLBACK_WEBHOOK_SECRET="${CDP_DEV_CALLBACK_WEBHOOK_SECRET:-}"
CDP_DEV_MUVSTOK_CALLBACK_WEBHOOK_SECRET="${CDP_DEV_MUVSTOK_CALLBACK_WEBHOOK_SECRET:-}"
CDP_DEV_WEBHOOK_URL="${CDP_DEV_WEBHOOK_URL:-https://automacao.tktechnologies.com.br/}"
CDP_DEV_N8N_WEBHOOK_PATH="${CDP_DEV_N8N_WEBHOOK_PATH:-webhook/dev-scraper-result}"
CDP_DEV_MUVSTOK_WEBHOOK_PATH="${CDP_DEV_MUVSTOK_WEBHOOK_PATH:-webhook/dev-muvstok-result}"
CDP_DEV_NOTIFIER_WEBHOOK_PATH="${CDP_DEV_NOTIFIER_WEBHOOK_PATH:-webhook/dev-cdp-notifier}"
CDP_DEV_RESULTADOS_SHEETS_URL="${CDP_DEV_RESULTADOS_SHEETS_URL:-}"
CDP_DEV_NOTIFICATION_EMAIL_TO="${CDP_DEV_NOTIFICATION_EMAIL_TO:-}"
CDP_DEV_PROGRESS_INTERVAL_MIN="${CDP_DEV_PROGRESS_INTERVAL_MIN:-10}"
CDP_DEV_PROGRESS_MIN_SKUS="${CDP_DEV_PROGRESS_MIN_SKUS:-15}"
CDP_DEV_PROGRESS_MIN_STEP_PCT="${CDP_DEV_PROGRESS_MIN_STEP_PCT:-10}"
CDP_DEV_PROGRESS_MAX_MESSAGES="${CDP_DEV_PROGRESS_MAX_MESSAGES:-6}"
CDP_DEV_SCRAPER_BATCH_SIZE="${CDP_DEV_SCRAPER_BATCH_SIZE:-}"
CDP_DEV_SCRAPER_SITES="${CDP_DEV_SCRAPER_SITES:-}"

SECRET_ARGS=(
  "telegram-dev-bot-token=${TELEGRAM_DEV_BOT_TOKEN}"
)
if [[ -n "${CDP_DEV_API_KEY}" ]]; then
  SECRET_ARGS+=("cdp-dev-api-key=${CDP_DEV_API_KEY}")
fi
if [[ -n "${CDP_DEV_MUVSTOK_API_KEY}" ]]; then
  SECRET_ARGS+=("cdp-dev-muvstok-api-key=${CDP_DEV_MUVSTOK_API_KEY}")
fi
if [[ -n "${CDP_DEV_CALLBACK_WEBHOOK_SECRET}" ]]; then
  SECRET_ARGS+=("cdp-dev-callback-webhook-secret=${CDP_DEV_CALLBACK_WEBHOOK_SECRET}")
fi
if [[ -n "${CDP_DEV_MUVSTOK_CALLBACK_WEBHOOK_SECRET}" ]]; then
  SECRET_ARGS+=("cdp-dev-muvstok-callback-webhook-secret=${CDP_DEV_MUVSTOK_CALLBACK_WEBHOOK_SECRET}")
fi

echo "==> Patch secrets on ${APP} (${RG})"
az containerapp secret set -g "${RG}" -n "${APP}" --secrets "${SECRET_ARGS[@]}" --output none

ENV_ARGS=(
  "CDP_ENV=shared"
  "TELEGRAM_DEV_ALLOWED_CHAT_IDS=${TELEGRAM_DEV_ALLOWED_CHAT_IDS}"
  "TELEGRAM_DEV_BOT_TOKEN=secretref:telegram-dev-bot-token"
  "CDP_DEV_SCRAPER_API_BASE=${CDP_DEV_SCRAPER_API_BASE}"
  "CDP_DEV_SKUS_SHEET_ID=${CDP_DEV_SKUS_SHEET_ID}"
  "CDP_DEV_RESULTADOS_SHEET_ID=${CDP_DEV_RESULTADOS_SHEET_ID}"
  "CDP_DEV_WEBHOOK_URL=${CDP_DEV_WEBHOOK_URL}"
  "CDP_DEV_N8N_WEBHOOK_PATH=${CDP_DEV_N8N_WEBHOOK_PATH}"
  "CDP_DEV_MUVSTOK_WEBHOOK_PATH=${CDP_DEV_MUVSTOK_WEBHOOK_PATH}"
  "CDP_DEV_NOTIFIER_WEBHOOK_PATH=${CDP_DEV_NOTIFIER_WEBHOOK_PATH}"
  "CDP_DEV_PROGRESS_INTERVAL_MIN=${CDP_DEV_PROGRESS_INTERVAL_MIN}"
  "CDP_DEV_PROGRESS_MIN_SKUS=${CDP_DEV_PROGRESS_MIN_SKUS}"
  "CDP_DEV_PROGRESS_MIN_STEP_PCT=${CDP_DEV_PROGRESS_MIN_STEP_PCT}"
  "CDP_DEV_PROGRESS_MAX_MESSAGES=${CDP_DEV_PROGRESS_MAX_MESSAGES}"
)

optional_env() {
  local key="$1"
  local value="$2"
  if [[ -n "${value}" ]]; then
    ENV_ARGS+=("${key}=${value}")
  fi
}

optional_env CDP_DEV_MUVSTOK_API_BASE "${CDP_DEV_MUVSTOK_API_BASE}"
optional_env CDP_DEV_RESULTADOS_SHEETS_URL "${CDP_DEV_RESULTADOS_SHEETS_URL}"
optional_env CDP_DEV_NOTIFICATION_EMAIL_TO "${CDP_DEV_NOTIFICATION_EMAIL_TO}"
optional_env CDP_DEV_SCRAPER_BATCH_SIZE "${CDP_DEV_SCRAPER_BATCH_SIZE}"
optional_env CDP_DEV_SCRAPER_SITES "${CDP_DEV_SCRAPER_SITES}"

if [[ -n "${CDP_DEV_API_KEY}" ]]; then
  ENV_ARGS+=("CDP_DEV_API_KEY=secretref:cdp-dev-api-key")
fi
if [[ -n "${CDP_DEV_MUVSTOK_API_KEY}" ]]; then
  ENV_ARGS+=("CDP_DEV_MUVSTOK_API_KEY=secretref:cdp-dev-muvstok-api-key")
fi
if [[ -n "${CDP_DEV_CALLBACK_WEBHOOK_SECRET}" ]]; then
  ENV_ARGS+=("CDP_DEV_CALLBACK_WEBHOOK_SECRET=secretref:cdp-dev-callback-webhook-secret")
fi
if [[ -n "${CDP_DEV_MUVSTOK_CALLBACK_WEBHOOK_SECRET}" ]]; then
  ENV_ARGS+=("CDP_DEV_MUVSTOK_CALLBACK_WEBHOOK_SECRET=secretref:cdp-dev-muvstok-callback-webhook-secret")
fi

echo "==> Update DEV env vars on ${APP}"
az containerapp update -g "${RG}" -n "${APP}" --set-env-vars "${ENV_ARGS[@]}" --output none

echo "Configured shared n8n DEV environment on ${APP}"
