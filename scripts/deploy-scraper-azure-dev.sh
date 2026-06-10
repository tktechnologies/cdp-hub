#!/usr/bin/env bash
# Deploy CDP scraper **development** stack (separate KV, Postgres, Redis, Container Apps).
set -euo pipefail
export PYTHONIOENCODING="${PYTHONIOENCODING:-utf-8}"

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SCRAPERS_DIR="${REPO_ROOT}/scrapers"
BICEP_TEMPLATE="${REPO_ROOT}/infra/scraper-stack.bicep"

RESOURCE_GROUP="${RESOURCE_GROUP:-automation}"
APP_LOCATION="${APP_LOCATION:-eastus2}"
POSTGRES_LOCATION="${POSTGRES_LOCATION:-brazilsouth}"
ACR_NAME="${ACR_NAME:-cdpscraperprodacr}"
IMAGE_NAME="${IMAGE_NAME:-cdp-scraper}"
IMAGE_TAG="${IMAGE_TAG:-dev-$(date +%Y%m%d-%H%M)}"
IMAGE_REF="${ACR_NAME}.azurecr.io/${IMAGE_NAME}:${IMAGE_TAG}"

KEY_VAULT_NAME="${KEY_VAULT_NAME:-cdp-scrapers-kv-dev}"
POSTGRES_SERVER_NAME="${POSTGRES_SERVER_NAME:-cdp-scrapers-pg-dev}"
POSTGRES_DATABASE_NAME="${POSTGRES_DATABASE_NAME:-cdp_scraper_dev}"
API_APP_NAME="${API_APP_NAME:-cdp-scrapers-api-dev}"
WORKER_APP_NAME="${WORKER_APP_NAME:-cdp-scrapers-worker-dev}"
N8N_APP_NAME="${N8N_APP_NAME:-cdp-n8n-dev}"
CONTAINER_APP_ENV="${CONTAINER_APP_ENV:-cdp-scrapers-dev-env}"

POSTGRES_ADMIN_USER="${POSTGRES_ADMIN_USER:-cdp}"
POSTGRES_ADMIN_PASSWORD="${POSTGRES_ADMIN_PASSWORD:-$(openssl rand -hex 24)}"
API_KEY="${API_KEY:-dev-$(openssl rand -hex 16)}"
CALLBACK_WEBHOOK_SECRET="${CALLBACK_WEBHOOK_SECRET:-$(openssl rand -hex 32)}"
PROXY_URLS="${PROXY_URLS:-[]}"
N8N_ENCRYPTION_KEY="${N8N_ENCRYPTION_KEY:-$(openssl rand -hex 32)}"
N8N_BASIC_AUTH_USER="${N8N_BASIC_AUTH_USER:-admin}"
N8N_BASIC_AUTH_PASSWORD="${N8N_BASIC_AUTH_PASSWORD:-$(openssl rand -hex 24)}"

echo "=== CDP scraper DEVELOPMENT deploy ==="
echo "RG=${RESOURCE_GROUP} KV=${KEY_VAULT_NAME} API=${API_APP_NAME}"
echo "Image: ${IMAGE_REF}"

az group create --name "${RESOURCE_GROUP}" --location "${APP_LOCATION}" --output none

COMMON_PARAMETERS=(
  environmentName=development
  acrName="${ACR_NAME}"
  containerAppEnvironmentName="${CONTAINER_APP_ENV}"
  apiContainerAppName="${API_APP_NAME}"
  workerContainerAppName="${WORKER_APP_NAME}"
  n8nContainerAppName="${N8N_APP_NAME}"
  imageName="${IMAGE_REF}"
  postgresServerName="${POSTGRES_SERVER_NAME}"
  postgresDatabaseName="${POSTGRES_DATABASE_NAME}"
  redisName=cdp-scrapers-redis-dev
  keyVaultName="${KEY_VAULT_NAME}"
  postgresAdminPassword="${POSTGRES_ADMIN_PASSWORD}"
  apiKey="${API_KEY}"
  callbackWebhookSecret="${CALLBACK_WEBHOOK_SECRET}"
  proxyUrls="${PROXY_URLS}"
  n8nEncryptionKey="${N8N_ENCRYPTION_KEY}"
  n8nBasicAuthUser="${N8N_BASIC_AUTH_USER}"
  n8nBasicAuthPassword="${N8N_BASIC_AUTH_PASSWORD}"
  deployContainerApps=false
)

CORE_NAME="cdp-dev-core-$(date +%Y%m%d%H%M%S)"
echo "Provisioning dev core (no apps)..."
az deployment group create \
  --name "${CORE_NAME}" \
  --resource-group "${RESOURCE_GROUP}" \
  --template-file "${BICEP_TEMPLATE}" \
  --parameters "${COMMON_PARAMETERS[@]}" \
  --output none

echo "Building image..."
az acr build --registry "${ACR_NAME}" --image "${IMAGE_NAME}:${IMAGE_TAG}" --no-logs "${SCRAPERS_DIR}"

POSTGRES_HOST="$(az postgres flexible-server show \
  --name "${POSTGRES_SERVER_NAME}" \
  --resource-group "${RESOURCE_GROUP}" \
  --query fullyQualifiedDomainName -o tsv | tr -d '\r')"
DATABASE_URL="postgresql+asyncpg://${POSTGRES_ADMIN_USER}:${POSTGRES_ADMIN_PASSWORD}@${POSTGRES_HOST}/${POSTGRES_DATABASE_NAME}?ssl=require"
DATABASE_URL_SYNC="postgresql://${POSTGRES_ADMIN_USER}:${POSTGRES_ADMIN_PASSWORD}@${POSTGRES_HOST}/${POSTGRES_DATABASE_NAME}?sslmode=require"

DEPLOY_CLIENT_IP="$(curl -fsS https://api.ipify.org | tr -d '\r\n')"
az postgres flexible-server firewall-rule create \
  --name "${POSTGRES_SERVER_NAME}" \
  --resource-group "${RESOURCE_GROUP}" \
  --rule-name deploy-client \
  --start-ip-address "${DEPLOY_CLIENT_IP}" \
  --end-ip-address "${DEPLOY_CLIENT_IP}" \
  --output none 2>/dev/null || true

cd "${SCRAPERS_DIR}"
UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/uv-cache}" \
  DATABASE_URL="${DATABASE_URL}" \
  DATABASE_URL_SYNC="${DATABASE_URL_SYNC}" \
  uv run alembic upgrade head

APPS_NAME="cdp-dev-apps-$(date +%Y%m%d%H%M%S)"
az deployment group create \
  --name "${APPS_NAME}" \
  --resource-group "${RESOURCE_GROUP}" \
  --template-file "${BICEP_TEMPLATE}" \
  --parameters "${COMMON_PARAMETERS[@]}" deployContainerApps=true \
  --output none

API_FQDN="$(az containerapp show -g "${RESOURCE_GROUP}" -n "${API_APP_NAME}" \
  --query properties.configuration.ingress.fqdn -o tsv)"
echo "DEV API: https://${API_FQDN}"
echo "DEV API_KEY (store in KV): ${API_KEY}"
echo "DEV Key Vault: ${KEY_VAULT_NAME}"
