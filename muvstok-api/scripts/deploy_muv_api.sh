#!/usr/bin/env bash
# Build and deploy cdp-muv-api (FastAPI / uvicorn) on Azure Container Apps.
set -euo pipefail
export PYTHONIOENCODING="${PYTHONIOENCODING:-utf-8}"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RG="${RG:-automation}"
ACR="${ACR:-cdpscraperprodacr}"
API_APP="${API_APP:-cdp-muv-api}"
TAG="${TAG:-$(date +%Y%m%d-%H%M)}"
API_IMAGE="${ACR}.azurecr.io/cdp-muv-api:${TAG}"
KV="${KV:-cdp-scrapers-kv-prod}"

echo "==> ACR build API image ${API_IMAGE} (Dockerfile.api)"
cd "${ROOT}"
az acr build --registry "${ACR}" --image "cdp-muv-api:${TAG}" -f docker/Dockerfile.api .

echo "==> Patch secrets on ${API_APP}"
DB_URL="$(az keyvault secret show --vault-name "${KV}" --name database-url --query value -o tsv)"
REDIS_URL="$(az keyvault secret show --vault-name "${KV}" --name redis-url --query value -o tsv)"
CB_SECRET="$(az keyvault secret show --vault-name "${KV}" --name callback-webhook-secret --query value -o tsv)"
API_KEY="$(az keyvault secret show --vault-name "${KV}" --name api-key --query value -o tsv 2>/dev/null || true)"

if [[ -z "${MUVSTOK_USER:-}" || -z "${MUVSTOK_PASSWORD:-}" ]]; then
  BACKUP_ENV="${BACKUP_ENV:-/home/devzurc/projects/backups/carparts-price-webscraper-backup-muvstok/.env}"
  if [[ -f "${BACKUP_ENV}" ]]; then
    # shellcheck disable=SC1090
    set -a && source "${BACKUP_ENV}" && set +a
    MUVSTOK_USER="${MUVSTOK_USER:-${CREDENTIAL_MUVSTOK_USER:-}}"
    MUVSTOK_PASSWORD="${MUVSTOK_PASSWORD:-${CREDENTIAL_MUVSTOK_PASS:-}}"
  fi
fi

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
az containerapp secret set -n "${API_APP}" -g "${RG}" --secrets "${SECRET_ARGS[@]}"

ENV_ARGS=(
  "ENVIRONMENT=azure-prod"
  "ENABLE_DOCS=true"
  "APP_NAME=API Diversos"
  "AZURE_KEY_VAULT_URL=https://cdp-scrapers-kv-prod.vault.azure.net/"
  "DATABASE_URL=secretref:database-url"
  "REDIS_URL=secretref:redis-url"
  "CALLBACK_WEBHOOK_SECRET=secretref:callback-webhook-secret"
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

echo "==> Update ${API_APP} -> ${API_IMAGE}"
az containerapp update -n "${API_APP}" -g "${RG}" \
  --image "${API_IMAGE}" \
  --set-env-vars "${ENV_ARGS[@]}"

echo "Done. API: ${API_APP} image ${API_IMAGE}"
