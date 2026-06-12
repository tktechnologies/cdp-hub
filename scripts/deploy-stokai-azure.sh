#!/usr/bin/env bash
# Deploy the STOKAI production stack in RG stokai-tk.
# This deploys Scraper + StokAPI resources and intentionally skips n8n.
set -euo pipefail
export PYTHONIOENCODING="${PYTHONIOENCODING:-utf-8}"

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

SOURCE_RESOURCE_GROUP="${SOURCE_RESOURCE_GROUP:-automation}"
SOURCE_KEY_VAULT_NAME="${SOURCE_KEY_VAULT_NAME:-cdp-scrapers-kv-prod}"

export RESOURCE_GROUP="${RESOURCE_GROUP:-stokai-tk}"
export APP_LOCATION="${APP_LOCATION:-eastus2}"
export POSTGRES_LOCATION="${POSTGRES_LOCATION:-brazilsouth}"
export ACR_NAME="${ACR_NAME:-cdpstokaitkacr}"
export PULL_IDENTITY_NAME="${PULL_IDENTITY_NAME:-cdp-stokai-prod-pull}"
export KEY_VAULT_NAME="${KEY_VAULT_NAME:-cdp-stokai-kv-prod}"
export POSTGRES_SERVER_NAME="${POSTGRES_SERVER_NAME:-cdp-stokai-pg-prod}"
export POSTGRES_DATABASE_NAME="${POSTGRES_DATABASE_NAME:-cdp_scraper}"
export REDIS_NAME="${REDIS_NAME:-cdp-stokai-redis-prod}"
export API_APP_NAME="${API_APP_NAME:-cdp-stokai-scrapers-api-prod}"
export WORKER_APP_NAME="${WORKER_APP_NAME:-cdp-stokai-scrapers-worker-prod}"
export CONTAINER_APP_ENV="${CONTAINER_APP_ENV:-cdp-stokai-prod-env}"
export DEPLOY_N8N="${DEPLOY_N8N:-false}"
export DEPLOY_PROXY_POOL="${DEPLOY_PROXY_POOL:-false}"
export PROXY_ROTATION_ENABLED="${PROXY_ROTATION_ENABLED:-true}"
export IMAGE_TAG="${IMAGE_TAG:-$(date +%Y%m%d-%H%M)}"

DEPLOY_SCRAPER_STACK="${DEPLOY_SCRAPER_STACK:-true}"
DEPLOY_STOKAPI="${DEPLOY_STOKAPI:-true}"
DEPLOY_STOKAPI_API="${DEPLOY_STOKAPI_API:-true}"
DEPLOY_STOKAPI_WORKER="${DEPLOY_STOKAPI_WORKER:-true}"
RUN_STOKAPI_MIGRATIONS="${RUN_STOKAPI_MIGRATIONS:-true}"

cleanup_stokapi_firewall() {
  if [[ -n "${STOKAPI_FIREWALL_RULE_CREATED:-}" ]]; then
    az postgres flexible-server firewall-rule delete \
      --name "${POSTGRES_SERVER_NAME}" \
      --resource-group "${RESOURCE_GROUP}" \
      --rule-name "${STOKAPI_FIREWALL_RULE_NAME}" \
      --yes \
      --output none 2>/dev/null || true
  fi
}
trap cleanup_stokapi_firewall EXIT

source_secret() {
  local name="$1"
  az keyvault secret show \
    --vault-name "${SOURCE_KEY_VAULT_NAME}" \
    --name "${name}" \
    --query value \
    -o tsv 2>/dev/null | tr -d '\r' || true
}

usable_secret() {
  local value="$1"
  if [[ -z "${value}" || "${value}" == "not-configured" ]]; then
    return 1
  fi
  printf '%s' "${value}"
}

if [[ -z "${MELIBOX_USER:-}" ]]; then
  MELIBOX_USER="$(usable_secret "$(source_secret melibox-user)" || true)"
fi
if [[ -z "${MELIBOX_PASS:-}" ]]; then
  MELIBOX_PASS="$(usable_secret "$(source_secret melibox-pass)" || true)"
fi
if [[ -z "${PROXY_URLS:-}" ]]; then
  PROXY_URLS="$(usable_secret "$(source_secret proxy-urls)" || true)"
fi
if [[ -z "${MUVSTOK_USER:-}" ]]; then
  MUVSTOK_USER="$(usable_secret "$(source_secret muvstok-user)" || true)"
fi
if [[ -z "${MUVSTOK_PASSWORD:-}" ]]; then
  MUVSTOK_PASSWORD="$(usable_secret "$(source_secret muvstok-password)" || true)"
fi

export MELIBOX_USER="${MELIBOX_USER:-}"
export MELIBOX_PASS="${MELIBOX_PASS:-}"
export PROXY_URLS="${PROXY_URLS:-[]}"
if [[ "${PROXY_ROTATION_ENABLED}" == "true" ]]; then
  case "${PROXY_URLS}" in
    ""|"[]"|"not-configured")
      export PROXY_ROTATION_ENABLED=false
      ;;
  esac
fi
export MUVSTOK_USER="${MUVSTOK_USER:-}"
export MUVSTOK_PASSWORD="${MUVSTOK_PASSWORD:-}"

echo "=== STOKAI production deploy ==="
echo "RG=${RESOURCE_GROUP} ACR=${ACR_NAME} KV=${KEY_VAULT_NAME}"
echo "Scraper API=${API_APP_NAME} worker=${WORKER_APP_NAME}"
echo "n8n deploy=${DEPLOY_N8N} (expected false)"

if [[ "${DEPLOY_SCRAPER_STACK}" == "true" ]]; then
  bash "${ROOT}/scripts/deploy-scraper-azure.sh"
fi

if [[ "${DEPLOY_STOKAPI}" != "true" ]]; then
  echo "Skipping StokAPI deploy."
  exit 0
fi

if [[ "${RUN_STOKAPI_MIGRATIONS}" == "true" ]]; then
  echo "Running STOKAI StokAPI migrations..."
  STOKAPI_DEPLOY_CLIENT_IP="$(curl -fsS https://api.ipify.org | tr -d '\r\n')"
  STOKAPI_FIREWALL_RULE_NAME="${STOKAPI_FIREWALL_RULE_NAME:-cdp-stokai-deploy-client}"
  az postgres flexible-server firewall-rule delete \
    --name "${POSTGRES_SERVER_NAME}" \
    --resource-group "${RESOURCE_GROUP}" \
    --rule-name "${STOKAPI_FIREWALL_RULE_NAME}" \
    --yes \
    --output none 2>/dev/null || true
  az postgres flexible-server firewall-rule create \
    --name "${POSTGRES_SERVER_NAME}" \
    --resource-group "${RESOURCE_GROUP}" \
    --rule-name "${STOKAPI_FIREWALL_RULE_NAME}" \
    --start-ip-address "${STOKAPI_DEPLOY_CLIENT_IP}" \
    --end-ip-address "${STOKAPI_DEPLOY_CLIENT_IP}" \
    --output none
  STOKAPI_FIREWALL_RULE_CREATED=true
  DB_URL="$(az keyvault secret show --vault-name "${KEY_VAULT_NAME}" --name database-url --query value -o tsv | tr -d '\r')"
  cd "${ROOT}/muvstok-api"
  UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/uv-cache}" DATABASE_URL="${DB_URL}" uv run alembic upgrade head
fi

COMMON_STOKAPI_ENV=(
  "RG=${RESOURCE_GROUP}"
  "ACR=${ACR_NAME}"
  "KV=${KEY_VAULT_NAME}"
  "ENV_NAME=${CONTAINER_APP_ENV}"
  "MI_NAME=${PULL_IDENTITY_NAME}"
  "AZURE_KEY_VAULT_URL=https://${KEY_VAULT_NAME}.vault.azure.net/"
  "ENVIRONMENT=azure-prod"
)

if [[ "${DEPLOY_STOKAPI_API}" == "true" ]]; then
  echo "Deploying STOKAI StokAPI API..."
  env "${COMMON_STOKAPI_ENV[@]}" \
    API_APP="${STOKAPI_API_APP:-cdp-stokai-muv-api}" \
    TAG="${TAG:-${IMAGE_TAG}}" \
    bash "${ROOT}/muvstok-api/scripts/deploy_muv_api.sh"
fi

if [[ "${DEPLOY_STOKAPI_WORKER}" == "true" ]]; then
  echo "Deploying STOKAI StokAPI worker..."
  env "${COMMON_STOKAPI_ENV[@]}" \
    API_APP="${STOKAPI_API_APP:-cdp-stokai-muv-api}" \
    WORKER_APP="${STOKAPI_WORKER_APP:-cdp-stokai-muv-worker}" \
    WORKER_INGRESS_ENABLED=false \
    TAG="${TAG:-${IMAGE_TAG}}" \
    bash "${ROOT}/muvstok-api/scripts/deploy_muv_worker.sh"
fi

echo "=== STOKAI deploy complete ==="
