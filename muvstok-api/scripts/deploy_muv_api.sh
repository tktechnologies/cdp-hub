#!/usr/bin/env bash
# Build and deploy cdp-muv-api (FastAPI / uvicorn) on Azure Container Apps.
set -euo pipefail
export PYTHONIOENCODING="${PYTHONIOENCODING:-utf-8}"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RG="${RG:-${RESOURCE_GROUP:-automation}}"
ACR="${ACR:-${ACR_NAME:-cdpscraperprodacr}}"
API_APP="${API_APP:-cdp-muv-api}"
TAG="${TAG:-$(date +%Y%m%d-%H%M)}"
API_IMAGE="${ACR}.azurecr.io/cdp-muv-api:${TAG}"
KV="${KV:-${KEY_VAULT_NAME:-cdp-scrapers-kv-prod}}"
ENV_NAME="${ENV_NAME:-cdp-scrapers-prod-env}"
MI_NAME="${MI_NAME:-cdp-scrapers-prod-pull}"
ENVIRONMENT="${ENVIRONMENT:-azure-prod}"
APP_NAME="${APP_NAME:-API Diversos}"
AZURE_KEY_VAULT_URL="${AZURE_KEY_VAULT_URL:-https://${KV}.vault.azure.net/}"

kv_secret() {
  local name="$1"
  az keyvault secret show --vault-name "${KV}" --name "${name}" --query value -o tsv 2>/dev/null | tr -d '\r' || true
}

require_value() {
  local name="$1"
  if [[ -z "${!name:-}" ]]; then
    echo "Missing required value: ${name}" >&2
    exit 1
  fi
}

resolve_muvstok_credentials() {
  MUVSTOK_USER="${MUVSTOK_USER:-$(kv_secret muvstok-user)}"
  MUVSTOK_PASSWORD="${MUVSTOK_PASSWORD:-$(kv_secret muvstok-password)}"
  if [[ "${MUVSTOK_USER:-}" == "not-configured" ]]; then MUVSTOK_USER=""; fi
  if [[ "${MUVSTOK_PASSWORD:-}" == "not-configured" ]]; then MUVSTOK_PASSWORD=""; fi
  if [[ -z "${MUVSTOK_USER:-}" || -z "${MUVSTOK_PASSWORD:-}" ]]; then
    BACKUP_ENV="${BACKUP_ENV:-/home/devzurc/projects/backups/carparts-price-webscraper-backup-muvstok/.env}"
    if [[ -f "${BACKUP_ENV}" ]]; then
      # shellcheck disable=SC1090
      set -a && source "${BACKUP_ENV}" && set +a
      MUVSTOK_USER="${MUVSTOK_USER:-${CREDENTIAL_MUVSTOK_USER:-}}"
      MUVSTOK_PASSWORD="${MUVSTOK_PASSWORD:-${CREDENTIAL_MUVSTOK_PASS:-}}"
    fi
  fi
}

echo "==> ACR build API image ${API_IMAGE} (Dockerfile.api)"
cd "${ROOT}"
az acr build --registry "${ACR}" --image "cdp-muv-api:${TAG}" -f docker/Dockerfile.api . --no-logs

echo "==> Resolve secrets for ${API_APP}"
DB_URL="$(kv_secret database-url)"
REDIS_URL="$(kv_secret redis-url)"
CB_SECRET="$(kv_secret callback-webhook-secret)"
API_KEY="$(kv_secret api-key)"
require_value DB_URL
require_value REDIS_URL
require_value CB_SECRET

resolve_muvstok_credentials

SECRET_ARGS=(
  "database-url=${DB_URL}"
  "redis-url=${REDIS_URL}"
  "callback-webhook-secret=${CB_SECRET}"
)
if [[ -n "${API_KEY}" ]]; then
  SECRET_ARGS+=("api-keys=${API_KEY}")
fi
if [[ -n "${MUVSTOK_USER:-}" && -n "${MUVSTOK_PASSWORD:-}" ]]; then
  SECRET_ARGS+=("muvstok-user=${MUVSTOK_USER}" "muvstok-password=${MUVSTOK_PASSWORD}")
fi

ENV_ARGS=(
  "ENVIRONMENT=${ENVIRONMENT}"
  "ENABLE_DOCS=true"
  "APP_NAME=${APP_NAME}"
  "AZURE_KEY_VAULT_URL=${AZURE_KEY_VAULT_URL}"
  "DATABASE_URL=secretref:database-url"
  "REDIS_URL=secretref:redis-url"
  "CALLBACK_WEBHOOK_SECRET=secretref:callback-webhook-secret"
  "MUVSTOK_DEALERSHIP_DIRECTORY_URL_FALLBACK_ENABLED=true"
)
if [[ -n "${API_KEY}" ]]; then
  ENV_ARGS+=("API_KEYS=secretref:api-keys")
fi
if [[ -n "${MUVSTOK_USER:-}" && -n "${MUVSTOK_PASSWORD:-}" ]]; then
  ENV_ARGS+=(
    "MUVSTOK_USER=secretref:muvstok-user"
    "MUVSTOK_PASSWORD=secretref:muvstok-password"
  )
fi

if az containerapp show -n "${API_APP}" -g "${RG}" --output none 2>/dev/null; then
  echo "==> Update ${API_APP} -> ${API_IMAGE}"
  az containerapp secret set -n "${API_APP}" -g "${RG}" --secrets "${SECRET_ARGS[@]}" --output none
  az containerapp update -n "${API_APP}" -g "${RG}" \
    --image "${API_IMAGE}" \
    --set-env-vars "${ENV_ARGS[@]}" \
    --output none
else
  echo "==> Create ${API_APP} -> ${API_IMAGE}"
  MI_RESOURCE="${MI_RESOURCE:-$(az identity show -g "${RG}" -n "${MI_NAME}" --query id -o tsv 2>/dev/null | tr -d '\r' || true)}"
  require_value MI_RESOURCE
  az containerapp create -n "${API_APP}" -g "${RG}" \
    --environment "${ENV_NAME}" \
    --image "${API_IMAGE}" \
    --registry-server "${ACR}.azurecr.io" \
    --registry-identity "${MI_RESOURCE}" \
    --ingress external \
    --target-port 8000 \
    --min-replicas 1 --max-replicas 2 \
    --cpu 0.5 --memory 1Gi \
    --user-assigned "${MI_RESOURCE}" \
    --secrets "${SECRET_ARGS[@]}" \
    --env-vars "${ENV_ARGS[@]}" \
    --output none
fi

echo "Done. API: ${API_APP} image ${API_IMAGE}"
