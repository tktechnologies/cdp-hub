#!/usr/bin/env bash
# Deploy API Diversos dev Container Apps (expects dev Key Vault secrets).
set -euo pipefail
export PYTHONIOENCODING="${PYTHONIOENCODING:-utf-8}"

RG="${RG:-automation}"
ACR="${ACR:-cdpscraperprodacr}"
KV="${KV:-cdp-scrapers-kv-dev}"
TAG="${TAG:-dev-$(date +%Y%m%d-%H%M)}"
API_APP="${API_APP:-cdp-muv-api-dev}"
WORKER_APP="${WORKER_APP:-cdp-muv-worker-dev}"
ENV_NAME="${ENV_NAME:-cdp-scrapers-dev-env}"
MI_NAME="${MI_NAME:-cdp-scrapers-prod-pull}"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

kv_secret() {
  local name="$1"
  az keyvault secret show --vault-name "${KV}" --name "${name}" --query value -o tsv 2>/dev/null || true
}

resolve_muvstok_credentials() {
  MUVSTOK_USER="${MUVSTOK_USER:-$(kv_secret muvstok-user)}"
  MUVSTOK_PASSWORD="${MUVSTOK_PASSWORD:-$(kv_secret muvstok-password)}"
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

require_value() {
  local name="$1"
  if [[ -z "${!name:-}" ]]; then
    echo "Missing required value: ${name}" >&2
    exit 1
  fi
}

MI_RESOURCE="${MI_RESOURCE:-$(az identity show -g "${RG}" -n "${MI_NAME}" --query id -o tsv 2>/dev/null || true)}"
require_value MI_RESOURCE

DB_URL="$(kv_secret database-url)"
REDIS_URL="$(kv_secret redis-url)"
CB_SECRET="$(kv_secret callback-webhook-secret)"
API_KEY="$(kv_secret api-key)"
require_value DB_URL
require_value REDIS_URL
require_value CB_SECRET
require_value API_KEY

resolve_muvstok_credentials
require_value MUVSTOK_USER
require_value MUVSTOK_PASSWORD

echo "==> Dev API image"
az acr build --registry "${ACR}" --image "cdp-muv-api:${TAG}" -f docker/Dockerfile.api .

API_IMAGE="${ACR}.azurecr.io/cdp-muv-api:${TAG}"
if az containerapp show -g "${RG}" -n "${API_APP}" --output none 2>/dev/null; then
  az containerapp secret set -g "${RG}" -n "${API_APP}" --secrets \
    "database-url=${DB_URL}" \
    "redis-url=${REDIS_URL}" \
    "callback-webhook-secret=${CB_SECRET}" \
    "api-keys=${API_KEY}" \
    "muvstok-user=${MUVSTOK_USER}" \
    "muvstok-password=${MUVSTOK_PASSWORD}" \
    --output none
  az containerapp update -g "${RG}" -n "${API_APP}" \
    --image "${API_IMAGE}" \
    --set-env-vars \
      "ENVIRONMENT=azure-dev" \
      "ENABLE_DOCS=true" \
      "APP_NAME=API Diversos DEV" \
      "AZURE_KEY_VAULT_URL=https://${KV}.vault.azure.net/" \
      "DATABASE_URL=secretref:database-url" \
      "REDIS_URL=secretref:redis-url" \
      "CALLBACK_WEBHOOK_SECRET=secretref:callback-webhook-secret" \
      "API_KEYS=secretref:api-keys" \
      "MUVSTOK_USER=secretref:muvstok-user" \
      "MUVSTOK_PASSWORD=secretref:muvstok-password" \
    --output none
  echo "Updated ${API_APP}"
else
  echo "Creating ${API_APP}"
  az containerapp create -g "${RG}" -n "${API_APP}" \
    --environment "${ENV_NAME}" \
    --image "${API_IMAGE}" \
    --registry-server "${ACR}.azurecr.io" \
    --registry-identity "${MI_RESOURCE}" \
    --ingress external \
    --target-port 8000 \
    --min-replicas 1 --max-replicas 2 \
    --cpu 0.5 --memory 1Gi \
    --user-assigned "${MI_RESOURCE}" \
    --secrets \
      "database-url=${DB_URL}" \
      "redis-url=${REDIS_URL}" \
      "callback-webhook-secret=${CB_SECRET}" \
      "api-keys=${API_KEY}" \
      "muvstok-user=${MUVSTOK_USER}" \
      "muvstok-password=${MUVSTOK_PASSWORD}" \
    --env-vars \
      "ENVIRONMENT=azure-dev" \
      "ENABLE_DOCS=true" \
      "APP_NAME=API Diversos DEV" \
      "AZURE_KEY_VAULT_URL=https://${KV}.vault.azure.net/" \
      "DATABASE_URL=secretref:database-url" \
      "REDIS_URL=secretref:redis-url" \
      "CALLBACK_WEBHOOK_SECRET=secretref:callback-webhook-secret" \
      "API_KEYS=secretref:api-keys" \
      "MUVSTOK_USER=secretref:muvstok-user" \
      "MUVSTOK_PASSWORD=secretref:muvstok-password" \
    --output none
fi
API_FQDN="$(az containerapp show -g "${RG}" -n "${API_APP}" --query properties.configuration.ingress.fqdn -o tsv | tr -d '\r\n')"
echo "DEV API Diversos: https://${API_FQDN}"

echo "==> Dev worker image"
az acr build --registry "${ACR}" --image "cdp-muv-worker:${TAG}" -f docker/Dockerfile.worker .
WORKER_IMAGE="${ACR}.azurecr.io/cdp-muv-worker:${TAG}"
if az containerapp show -g "${RG}" -n "${WORKER_APP}" --output none 2>/dev/null; then
  az containerapp secret set -g "${RG}" -n "${WORKER_APP}" --secrets \
    "database-url=${DB_URL}" \
    "redis-url=${REDIS_URL}" \
    "callback-webhook-secret=${CB_SECRET}" \
    "muvstok-user=${MUVSTOK_USER}" \
    "muvstok-password=${MUVSTOK_PASSWORD}" \
    --output none
  az containerapp update -g "${RG}" -n "${WORKER_APP}" \
    --image "${WORKER_IMAGE}" \
    --min-replicas 1 --max-replicas 2 \
    --set-env-vars \
      "ENVIRONMENT=azure-dev" \
      "AZURE_KEY_VAULT_URL=https://${KV}.vault.azure.net/" \
      "REDIS_CONSUMER_NAME=cdp-muv-worker-dev-1" \
      "DATABASE_URL=secretref:database-url" \
      "REDIS_URL=secretref:redis-url" \
      "CALLBACK_WEBHOOK_SECRET=secretref:callback-webhook-secret" \
      "MUVSTOK_USER=secretref:muvstok-user" \
      "MUVSTOK_PASSWORD=secretref:muvstok-password" \
    --output none
  echo "Updated ${WORKER_APP}"
else
  echo "Creating ${WORKER_APP}"
  az containerapp create -g "${RG}" -n "${WORKER_APP}" \
    --environment "${ENV_NAME}" \
    --image "${WORKER_IMAGE}" \
    --registry-server "${ACR}.azurecr.io" \
    --registry-identity "${MI_RESOURCE}" \
    --ingress internal \
    --target-port 8080 \
    --min-replicas 1 --max-replicas 2 \
    --cpu 0.5 --memory 1Gi \
    --user-assigned "${MI_RESOURCE}" \
    --secrets \
      "database-url=${DB_URL}" \
      "redis-url=${REDIS_URL}" \
      "callback-webhook-secret=${CB_SECRET}" \
      "muvstok-user=${MUVSTOK_USER}" \
      "muvstok-password=${MUVSTOK_PASSWORD}" \
    --env-vars \
      "ENVIRONMENT=azure-dev" \
      "AZURE_KEY_VAULT_URL=https://${KV}.vault.azure.net/" \
      "REDIS_CONSUMER_NAME=cdp-muv-worker-dev-1" \
      "DATABASE_URL=secretref:database-url" \
      "REDIS_URL=secretref:redis-url" \
      "CALLBACK_WEBHOOK_SECRET=secretref:callback-webhook-secret" \
      "MUVSTOK_USER=secretref:muvstok-user" \
      "MUVSTOK_PASSWORD=secretref:muvstok-password" \
    --output none
fi
