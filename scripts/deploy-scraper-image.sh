#!/usr/bin/env bash
# Build and roll out scraper API + worker images (no Bicep / Postgres changes).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RG="${RESOURCE_GROUP:-automation}"
ACR="${ACR_NAME:-cdpscraperprodacr}"
TAG="${IMAGE_TAG:-$(date +%Y%m%d-%H%M)}"
API_APP="${API_APP_NAME:-cdp-scrapers-api-prod}"
WORKER_APP="${WORKER_APP_NAME:-cdp-scrapers-worker-prod}"
IMAGE_REF="${ACR}.azurecr.io/cdp-scraper:${TAG}"

echo "==> Build ${IMAGE_REF}"
cd "${ROOT}/scrapers"
if docker info >/dev/null 2>&1; then
  az acr login --name "${ACR}" --output none
  docker build -t "${IMAGE_REF}" .
  docker push "${IMAGE_REF}"
else
  az acr build --registry "${ACR}" --image "cdp-scraper:${TAG}" --no-logs .
fi

echo "==> Update Container Apps"
az containerapp update -g "${RG}" -n "${API_APP}" --image "${IMAGE_REF}" --output none
az containerapp update -g "${RG}" -n "${WORKER_APP}" --image "${IMAGE_REF}" --output none

echo "==> Health check"
API_FQDN="$(az containerapp show -g "${RG}" -n "${API_APP}" --query properties.configuration.ingress.fqdn -o tsv | tr -d '\r\n')"
curl -fsS "https://${API_FQDN}/api/v1/health"
echo
echo "Deployed ${IMAGE_REF} to ${API_APP} and ${WORKER_APP}"
