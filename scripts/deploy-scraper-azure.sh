#!/usr/bin/env bash
# Rebuild and deploy the CDP scraper production stack on Azure.
# Platform Bicep: infra/scraper-stack.bicep (orchestrated by infra/main.bicep).

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
IMAGE_TAG="${IMAGE_TAG:-latest}"
IMAGE_REF="${ACR_NAME}.azurecr.io/${IMAGE_NAME}:${IMAGE_TAG}"
POSTGRES_SERVER_NAME="${POSTGRES_SERVER_NAME:-cdp-scrapers-pg-prod}"
POSTGRES_DATABASE_NAME="${POSTGRES_DATABASE_NAME:-cdp_scraper}"
POSTGRES_ADMIN_USER="${POSTGRES_ADMIN_USER:-cdp}"
KEY_VAULT_NAME="${KEY_VAULT_NAME:-cdp-scrapers-kv-prod}"
API_APP_NAME="${API_APP_NAME:-cdp-scrapers-api-prod}"
WORKER_APP_NAME="${WORKER_APP_NAME:-cdp-scrapers-worker-prod}"
N8N_APP_NAME="${N8N_APP_NAME:-cdp-n8n-prod}"

POSTGRES_ADMIN_PASSWORD="${POSTGRES_ADMIN_PASSWORD:-}"
API_KEY="${API_KEY:-}"
CALLBACK_WEBHOOK_SECRET="${CALLBACK_WEBHOOK_SECRET:-}"
MELIBOX_USER="${MELIBOX_USER:-}"
MELIBOX_PASS="${MELIBOX_PASS:-}"
PROXY_URLS="${PROXY_URLS:-[]}"
PROXY_ROTATION_ENABLED="${PROXY_ROTATION_ENABLED:-true}"
DEPLOY_PROXY_POOL="${DEPLOY_PROXY_POOL:-false}"
PROXY_ADMIN_PASSWORD="${PROXY_ADMIN_PASSWORD:-}"
N8N_ENCRYPTION_KEY="${N8N_ENCRYPTION_KEY:-}"
N8N_BASIC_AUTH_USER="${N8N_BASIC_AUTH_USER:-admin}"
N8N_BASIC_AUTH_PASSWORD="${N8N_BASIC_AUTH_PASSWORD:-}"

if az keyvault show --name "${KEY_VAULT_NAME}" --resource-group "${RESOURCE_GROUP}" --output none 2>/dev/null; then
  EXISTING_DATABASE_URL="$(az keyvault secret show --vault-name "${KEY_VAULT_NAME}" --name database-url --query value -o tsv 2>/dev/null || true)"
  if [[ -n "${EXISTING_DATABASE_URL}" && -z "${POSTGRES_ADMIN_PASSWORD}" ]]; then
    POSTGRES_ADMIN_PASSWORD="$(printf '%s' "${EXISTING_DATABASE_URL}" | sed -E "s#.*://${POSTGRES_ADMIN_USER}:([^@]+)@.*#\\1#")"
  fi
  API_KEY="${API_KEY:-$(az keyvault secret show --vault-name "${KEY_VAULT_NAME}" --name api-key --query value -o tsv 2>/dev/null || true)}"
  CALLBACK_WEBHOOK_SECRET="${CALLBACK_WEBHOOK_SECRET:-$(az keyvault secret show --vault-name "${KEY_VAULT_NAME}" --name callback-webhook-secret --query value -o tsv 2>/dev/null || true)}"
  MELIBOX_USER="${MELIBOX_USER:-$(az keyvault secret show --vault-name "${KEY_VAULT_NAME}" --name melibox-user --query value -o tsv 2>/dev/null || true)}"
  MELIBOX_PASS="${MELIBOX_PASS:-$(az keyvault secret show --vault-name "${KEY_VAULT_NAME}" --name melibox-pass --query value -o tsv 2>/dev/null || true)}"
  PROXY_URLS="${PROXY_URLS:-$(az keyvault secret show --vault-name "${KEY_VAULT_NAME}" --name proxy-urls --query value -o tsv 2>/dev/null || true)}"
  N8N_ENCRYPTION_KEY="${N8N_ENCRYPTION_KEY:-$(az keyvault secret show --vault-name "${KEY_VAULT_NAME}" --name n8n-encryption-key --query value -o tsv 2>/dev/null || true)}"
  N8N_BASIC_AUTH_USER="${N8N_BASIC_AUTH_USER:-$(az keyvault secret show --vault-name "${KEY_VAULT_NAME}" --name n8n-basic-auth-user --query value -o tsv 2>/dev/null || true)}"
  N8N_BASIC_AUTH_PASSWORD="${N8N_BASIC_AUTH_PASSWORD:-$(az keyvault secret show --vault-name "${KEY_VAULT_NAME}" --name n8n-basic-auth-password --query value -o tsv 2>/dev/null || true)}"
fi

POSTGRES_ADMIN_PASSWORD="${POSTGRES_ADMIN_PASSWORD:-$(openssl rand -hex 24)}"
API_KEY="${API_KEY:-$(openssl rand -hex 32)}"
CALLBACK_WEBHOOK_SECRET="${CALLBACK_WEBHOOK_SECRET:-$(openssl rand -hex 32)}"
N8N_ENCRYPTION_KEY="${N8N_ENCRYPTION_KEY:-$(openssl rand -hex 32)}"
N8N_BASIC_AUTH_USER="${N8N_BASIC_AUTH_USER:-admin}"
N8N_BASIC_AUTH_PASSWORD="${N8N_BASIC_AUTH_PASSWORD:-$(openssl rand -hex 24)}"

echo "=== CDP scraper production rebuild ==="
echo "Resource group: ${RESOURCE_GROUP}"
echo "PostgreSQL location: ${POSTGRES_LOCATION}"
echo "App resources location: ${APP_LOCATION}"
echo "Image: ${IMAGE_REF}"

cleanup_deploy_firewall() {
  if [[ -n "${DEPLOY_FIREWALL_RULE_CREATED:-}" ]]; then
    az postgres flexible-server firewall-rule delete \
      --name "${POSTGRES_SERVER_NAME}" \
      --resource-group "${RESOURCE_GROUP}" \
      --rule-name "${DEPLOY_FIREWALL_RULE_NAME}" \
      --yes \
      --output none 2>/dev/null || true
  fi
}
trap cleanup_deploy_firewall EXIT

az group create \
  --name "${RESOURCE_GROUP}" \
  --location "${APP_LOCATION}" \
  --output none

COMMON_PARAMETERS=(
  appLocation="${APP_LOCATION}"
  postgresLocation="${POSTGRES_LOCATION}"
  acrName="${ACR_NAME}"
  imageName="${IMAGE_REF}"
  postgresServerName="${POSTGRES_SERVER_NAME}"
  postgresDatabaseName="${POSTGRES_DATABASE_NAME}"
  postgresAdminUser="${POSTGRES_ADMIN_USER}"
  postgresAdminPassword="${POSTGRES_ADMIN_PASSWORD}"
  keyVaultName="${KEY_VAULT_NAME}"
  apiContainerAppName="${API_APP_NAME}"
  workerContainerAppName="${WORKER_APP_NAME}"
  n8nContainerAppName="${N8N_APP_NAME}"
  apiKey="${API_KEY}"
  callbackWebhookSecret="${CALLBACK_WEBHOOK_SECRET}"
  meliboxUser="${MELIBOX_USER}"
  meliboxPass="${MELIBOX_PASS}"
  proxyUrls="${PROXY_URLS}"
  proxyRotationEnabled="${PROXY_ROTATION_ENABLED}"
  deployProxyPool="${DEPLOY_PROXY_POOL}"
  proxyAdminPassword="${PROXY_ADMIN_PASSWORD}"
  n8nEncryptionKey="${N8N_ENCRYPTION_KEY}"
  n8nBasicAuthUser="${N8N_BASIC_AUTH_USER}"
  n8nBasicAuthPassword="${N8N_BASIC_AUTH_PASSWORD}"
)

CORE_DEPLOYMENT_NAME="cdp-prod-core-$(date +%Y%m%d%H%M%S)"
echo "Provisioning core infrastructure without Container Apps..."
az deployment group create \
  --name "${CORE_DEPLOYMENT_NAME}" \
  --resource-group "${RESOURCE_GROUP}" \
  --template-file "${BICEP_TEMPLATE}" \
  --parameters "${COMMON_PARAMETERS[@]}" deployContainerApps=false \
  --output none

echo "Building and pushing scraper image..."
az acr login --name "${ACR_NAME}" --output none
if docker info >/dev/null 2>&1; then
  docker build -t "${IMAGE_REF}" "${SCRAPERS_DIR}"
  docker push "${IMAGE_REF}"
else
  echo "Local Docker daemon unavailable; building remotely with Azure ACR..."
  az acr build \
    --registry "${ACR_NAME}" \
    --image "${IMAGE_NAME}:${IMAGE_TAG}" \
    --no-logs \
    "${SCRAPERS_DIR}"
fi

POSTGRES_HOST="$(az postgres flexible-server show \
  --name "${POSTGRES_SERVER_NAME}" \
  --resource-group "${RESOURCE_GROUP}" \
  --query fullyQualifiedDomainName \
  -o tsv | tr -d '\r')"

DATABASE_URL="postgresql+asyncpg://${POSTGRES_ADMIN_USER}:${POSTGRES_ADMIN_PASSWORD}@${POSTGRES_HOST}/${POSTGRES_DATABASE_NAME}?ssl=require"
DATABASE_URL_SYNC="postgresql://${POSTGRES_ADMIN_USER}:${POSTGRES_ADMIN_PASSWORD}@${POSTGRES_HOST}/${POSTGRES_DATABASE_NAME}?sslmode=require"

DEPLOY_CLIENT_IP="$(curl -fsS https://api.ipify.org | tr -d '\r\n')"
DEPLOY_FIREWALL_RULE_NAME="deploy-client"
echo "Temporarily allowing deployment client IP for migrations..."
az postgres flexible-server firewall-rule delete \
  --name "${POSTGRES_SERVER_NAME}" \
  --resource-group "${RESOURCE_GROUP}" \
  --rule-name "${DEPLOY_FIREWALL_RULE_NAME}" \
  --yes \
  --output none 2>/dev/null || true
az postgres flexible-server firewall-rule create \
  --name "${POSTGRES_SERVER_NAME}" \
  --resource-group "${RESOURCE_GROUP}" \
  --rule-name "${DEPLOY_FIREWALL_RULE_NAME}" \
  --start-ip-address "${DEPLOY_CLIENT_IP}" \
  --end-ip-address "${DEPLOY_CLIENT_IP}" \
  --output none
DEPLOY_FIREWALL_RULE_CREATED=true

echo "Running production database migrations..."
cd "${SCRAPERS_DIR}"
UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/uv-cache}" \
DATABASE_URL="${DATABASE_URL}" \
DATABASE_URL_SYNC="${DATABASE_URL_SYNC}" \
uv run alembic upgrade head

FULL_DEPLOYMENT_NAME="cdp-prod-apps-$(date +%Y%m%d%H%M%S)"
echo "Deploying API, worker, and N8N Container Apps..."
az deployment group create \
  --name "${FULL_DEPLOYMENT_NAME}" \
  --resource-group "${RESOURCE_GROUP}" \
  --template-file "${BICEP_TEMPLATE}" \
  --parameters "${COMMON_PARAMETERS[@]}" deployContainerApps=true \
  --output none

API_FQDN="$(az containerapp show \
  --name "${API_APP_NAME}" \
  --resource-group "${RESOURCE_GROUP}" \
  --query properties.configuration.ingress.fqdn \
  -o tsv | tr -d '\r')"
N8N_FQDN="$(az containerapp show \
  --name "${N8N_APP_NAME}" \
  --resource-group "${RESOURCE_GROUP}" \
  --query properties.configuration.ingress.fqdn \
  -o tsv | tr -d '\r')"

echo "Checking API health..."
curl -fsS "https://${API_FQDN}/api/v1/health"
echo

echo "Recent worker logs:"
az containerapp logs show \
  --name "${WORKER_APP_NAME}" \
  --resource-group "${RESOURCE_GROUP}" \
  --tail 100 || true

if [[ "${RUN_PRODUCTION_SMOKE:-false}" == "true" ]]; then
  echo "Running production scraper curl smoke tests..."
  API_BASE_URL="https://${API_FQDN}" \
  API_KEY="${API_KEY}" \
  N8N_BASE_URL="https://${N8N_FQDN}" \
  UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/uv-cache}" \
  uv run python scripts/production_scraper_curl_smoke.py \
    --manifest docs/validation/production_scraper_curl_cases.example.json \
    --output docs/validation/latest_production_curl_smoke.json
fi

echo "=== Deployment complete ==="
echo "API URL: https://${API_FQDN}"
echo "N8N URL: https://${N8N_FQDN}"
echo "Key Vault: ${KEY_VAULT_NAME}"
