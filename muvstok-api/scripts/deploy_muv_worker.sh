#!/usr/bin/env bash
# Deploy cdp-muv-worker Container App (Redis consumer) in RG automation.
set -euo pipefail
export PYTHONIOENCODING="${PYTHONIOENCODING:-utf-8}"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RG="${RG:-automation}"
ACR="${ACR:-cdpscraperprodacr}"
API_APP="${API_APP:-cdp-muv-api}"
WORKER_APP="${WORKER_APP:-cdp-muv-worker}"
MI_RESOURCE="${MI_RESOURCE:-/subscriptions/d2b27e51-47eb-47c8-bf64-66f63ef9f6aa/resourcegroups/automation/providers/Microsoft.ManagedIdentity/userAssignedIdentities/cdp-scrapers-prod-pull}"
TAG="${TAG:-$(date +%Y%m%d-%H%M)}"
WORKER_IMAGE="${ACR}.azurecr.io/cdp-muv-worker:${TAG}"

# Muvstok API credentials (Key Vault secrets muvstok-* may not exist yet).
if [[ -z "${MUVSTOK_USER:-}" || -z "${MUVSTOK_PASSWORD:-}" ]]; then
  BACKUP_ENV="${BACKUP_ENV:-/home/devzurc/projects/backups/carparts-price-webscraper-backup-muvstok/.env}"
  if [[ -f "${BACKUP_ENV}" ]]; then
    # shellcheck disable=SC1090
    set -a && source "${BACKUP_ENV}" && set +a
    MUVSTOK_USER="${MUVSTOK_USER:-${CREDENTIAL_MUVSTOK_USER:-}}"
    MUVSTOK_PASSWORD="${MUVSTOK_PASSWORD:-${CREDENTIAL_MUVSTOK_PASS:-}}"
  fi
fi
if [[ -z "${MUVSTOK_USER:-}" || -z "${MUVSTOK_PASSWORD:-}" ]]; then
  echo "Set MUVSTOK_USER and MUVSTOK_PASSWORD (or BACKUP_ENV with CREDENTIAL_MUVSTOK_*)" >&2
  exit 1
fi

echo "==> ACR build worker image ${WORKER_IMAGE} (Dockerfile.worker)"
cd "${ROOT}"
az acr build --registry "${ACR}" --image "cdp-muv-worker:${TAG}" -f docker/Dockerfile.worker .

echo "==> Resolve Container Apps environment"
ENV_ID="$(az containerapp show -n "${API_APP}" -g "${RG}" --query properties.managedEnvironmentId -o tsv)"
ENV_NAME="${ENV_NAME:-cdp-scrapers-prod-env}"
KV="${KV:-cdp-scrapers-kv-prod}"

# Prefer inline secrets (CLI can read KV); keyvaultref needs MI with vault access.
DB_URL="$(az keyvault secret show --vault-name "${KV}" --name database-url --query value -o tsv)"
REDIS_URL="$(az keyvault secret show --vault-name "${KV}" --name redis-url --query value -o tsv)"
CB_SECRET="$(az keyvault secret show --vault-name "${KV}" --name callback-webhook-secret --query value -o tsv)"

CA_SECRETS=(
  "database-url=${DB_URL}"
  "redis-url=${REDIS_URL}"
  "callback-webhook-secret=${CB_SECRET}"
  "muvstok-user=${MUVSTOK_USER}"
  "muvstok-password=${MUVSTOK_PASSWORD}"
)

ENV_VARS=(
  "ENVIRONMENT=azure-prod"
  "AZURE_KEY_VAULT_URL=https://cdp-scrapers-kv-prod.vault.azure.net/"
  "REDIS_CONSUMER_NAME=cdp-muv-worker-1"
  "DATABASE_URL=secretref:database-url"
  "REDIS_URL=secretref:redis-url"
  "CALLBACK_WEBHOOK_SECRET=secretref:callback-webhook-secret"
  "MUVSTOK_USER=secretref:muvstok-user"
  "MUVSTOK_PASSWORD=secretref:muvstok-password"
)

if az containerapp show -n "${WORKER_APP}" -g "${RG}" >/dev/null 2>&1; then
  echo "==> Update worker ${WORKER_APP}"
  az containerapp secret set -n "${WORKER_APP}" -g "${RG}" --secrets "${CA_SECRETS[@]}"
  az containerapp update -n "${WORKER_APP}" -g "${RG}" \
    --image "${WORKER_IMAGE}" \
    --min-replicas 1 --max-replicas 2 \
    --set-env-vars "${ENV_VARS[@]}"
else
  echo "==> Create worker ${WORKER_APP}"
  az containerapp create -n "${WORKER_APP}" -g "${RG}" \
    --environment "${ENV_NAME}" \
    --image "${WORKER_IMAGE}" \
    --registry-server "${ACR}.azurecr.io" \
    --registry-identity "${MI_RESOURCE}" \
    --ingress internal \
    --target-port 8080 \
    --min-replicas 1 --max-replicas 2 \
    --cpu 0.5 --memory 1Gi \
    --user-assigned "${MI_RESOURCE}" \
    --secrets "${CA_SECRETS[@]}" \
    --env-vars "${ENV_VARS[@]}"
fi

echo "Done. Worker: ${WORKER_APP} image ${WORKER_IMAGE}"
echo "Note: API (${API_APP}) is NOT updated by this script. Use scripts/deploy_muv_api.sh for FastAPI/uvicorn."
