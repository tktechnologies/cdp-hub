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

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

echo "==> Dev API image"
az acr build --registry "${ACR}" --image "cdp-muv-api:${TAG}" -f docker/Dockerfile.api .

API_IMAGE="${ACR}.azurecr.io/cdp-muv-api:${TAG}"
if az containerapp show -g "${RG}" -n "${API_APP}" --output none 2>/dev/null; then
  az containerapp update -g "${RG}" -n "${API_APP}" --image "${API_IMAGE}" --output none
  echo "Updated ${API_APP}"
else
  echo "Create ${API_APP} via infra/modules/stokapi-apps.bicep or portal first." >&2
  exit 1
fi

echo "==> Dev worker image"
az acr build --registry "${ACR}" --image "cdp-muv-worker:${TAG}" -f docker/Dockerfile.worker .
WORKER_IMAGE="${ACR}.azurecr.io/cdp-muv-worker:${TAG}"
if az containerapp show -g "${RG}" -n "${WORKER_APP}" --output none 2>/dev/null; then
  az containerapp update -g "${RG}" -n "${WORKER_APP}" --image "${WORKER_IMAGE}" --output none
  echo "Updated ${WORKER_APP}"
else
  echo "Skip worker — ${WORKER_APP} not found (provision StokAPI dev apps first)."
fi
