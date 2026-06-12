#!/usr/bin/env bash
# Deploy cdp-muv-worker Container App (Redis consumer).
set -euo pipefail
export PYTHONIOENCODING="${PYTHONIOENCODING:-utf-8}"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RG="${RG:-${RESOURCE_GROUP:-automation}}"
ACR="${ACR:-${ACR_NAME:-cdpscraperprodacr}}"
API_APP="${API_APP:-cdp-muv-api}"
WORKER_APP="${WORKER_APP:-cdp-muv-worker}"
ENV_NAME="${ENV_NAME:-cdp-scrapers-prod-env}"
MI_NAME="${MI_NAME:-cdp-scrapers-prod-pull}"
TAG="${TAG:-$(date +%Y%m%d-%H%M)}"
WORKER_IMAGE="${ACR}.azurecr.io/cdp-muv-worker:${TAG}"
KV="${KV:-${KEY_VAULT_NAME:-cdp-scrapers-kv-prod}}"
ENVIRONMENT="${ENVIRONMENT:-azure-prod}"
AZURE_KEY_VAULT_URL="${AZURE_KEY_VAULT_URL:-https://${KV}.vault.azure.net/}"
REDIS_CONSUMER_NAME="${REDIS_CONSUMER_NAME:-${WORKER_APP}-1}"
WORKER_INGRESS_ENABLED="${WORKER_INGRESS_ENABLED:-false}"
WORKER_TARGET_PORT="${WORKER_TARGET_PORT:-8080}"
WORKER_MIN_REPLICAS="${WORKER_MIN_REPLICAS:-1}"
WORKER_MAX_REPLICAS="${WORKER_MAX_REPLICAS:-1}"

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
  require_value MUVSTOK_USER
  require_value MUVSTOK_PASSWORD
}

resolve_muvstok_credentials

echo "==> ACR build worker image ${WORKER_IMAGE} (Dockerfile.worker)"
cd "${ROOT}"
az acr build --registry "${ACR}" --image "cdp-muv-worker:${TAG}" -f docker/Dockerfile.worker . --no-logs

echo "==> Resolve Container Apps environment"
if az containerapp show -n "${API_APP}" -g "${RG}" --output none 2>/dev/null; then
  ENV_ID="$(az containerapp show -n "${API_APP}" -g "${RG}" --query properties.managedEnvironmentId -o tsv | tr -d '\r')"
  ENV_NAME="${ENV_NAME:-${ENV_ID}}"
fi

DB_URL="$(kv_secret database-url)"
REDIS_URL="$(kv_secret redis-url)"
CB_SECRET="$(kv_secret callback-webhook-secret)"
require_value DB_URL
require_value REDIS_URL
require_value CB_SECRET

CA_SECRETS=(
  "database-url=${DB_URL}"
  "redis-url=${REDIS_URL}"
  "callback-webhook-secret=${CB_SECRET}"
  "muvstok-user=${MUVSTOK_USER}"
  "muvstok-password=${MUVSTOK_PASSWORD}"
)

ENV_VARS=(
  "ENVIRONMENT=${ENVIRONMENT}"
  "AZURE_KEY_VAULT_URL=${AZURE_KEY_VAULT_URL}"
  "REDIS_CONSUMER_NAME=${REDIS_CONSUMER_NAME}"
  "DATABASE_URL=secretref:database-url"
  "REDIS_URL=secretref:redis-url"
  "CALLBACK_WEBHOOK_SECRET=secretref:callback-webhook-secret"
  "MUVSTOK_USER=secretref:muvstok-user"
  "MUVSTOK_PASSWORD=secretref:muvstok-password"
  "MUVSTOK_DEALERSHIP_DIRECTORY_URL_FALLBACK_ENABLED=true"
)

if az containerapp show -n "${WORKER_APP}" -g "${RG}" --output none 2>/dev/null; then
  echo "==> Update worker ${WORKER_APP}"
  az containerapp secret set -n "${WORKER_APP}" -g "${RG}" --secrets "${CA_SECRETS[@]}" --output none
  az containerapp update -n "${WORKER_APP}" -g "${RG}" \
    --image "${WORKER_IMAGE}" \
    --min-replicas "${WORKER_MIN_REPLICAS}" --max-replicas "${WORKER_MAX_REPLICAS}" \
    --set-env-vars "${ENV_VARS[@]}" \
    --output none
  if [[ "${WORKER_INGRESS_ENABLED}" != "true" ]]; then
    az containerapp ingress disable -n "${WORKER_APP}" -g "${RG}" --output none
  fi
else
  echo "==> Create worker ${WORKER_APP}"
  MI_RESOURCE="${MI_RESOURCE:-$(az identity show -g "${RG}" -n "${MI_NAME}" --query id -o tsv 2>/dev/null | tr -d '\r' || true)}"
  require_value MI_RESOURCE
  INGRESS_ARGS=()
  if [[ "${WORKER_INGRESS_ENABLED}" == "true" ]]; then
    INGRESS_ARGS=(--ingress internal --target-port "${WORKER_TARGET_PORT}")
  fi
  az containerapp create -n "${WORKER_APP}" -g "${RG}" \
    --environment "${ENV_NAME}" \
    --image "${WORKER_IMAGE}" \
    --registry-server "${ACR}.azurecr.io" \
    --registry-identity "${MI_RESOURCE}" \
    "${INGRESS_ARGS[@]}" \
    --min-replicas "${WORKER_MIN_REPLICAS}" --max-replicas "${WORKER_MAX_REPLICAS}" \
    --cpu 0.5 --memory 1Gi \
    --user-assigned "${MI_RESOURCE}" \
    --secrets "${CA_SECRETS[@]}" \
    --env-vars "${ENV_VARS[@]}" \
    --output none
fi

echo "Done. Worker: ${WORKER_APP} image ${WORKER_IMAGE}"
echo "Note: API (${API_APP}) is NOT updated by this script. Use scripts/deploy_muv_api.sh for FastAPI/uvicorn."
