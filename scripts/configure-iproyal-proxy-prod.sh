#!/usr/bin/env bash
# Apply IPRoyal ISP BR proxy settings to CDP scraper Container Apps (prod + dev).
#
# Prerequisites:
#   - az login with Contributor on the target RG
#   - scrapers/.env with CREDENTIAL_MELIBOX_* and proxy URLs (or export PROXY_URLS JSON)
#
# Key Vault (cdp-scrapers-kv-prod): requires Secrets Officer — run manually if this script
# cannot write KV (see scrapers/docs/runbooks/iproyal-isp-proxy-setup.md §4).
#
# Before running: whitelist Azure outbound IP in IPRoyal dashboard
# (ISP → Whitelisted IPs). Check with:
#   az containerapp show -g "$RESOURCE_GROUP" -n "$WORKER_APP_NAME" \
#     --query 'properties.outboundIpAddresses[0]' -o tsv

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="${ENV_FILE:-${ROOT}/scrapers/.env}"
RG="${RESOURCE_GROUP:-automation}"
if [[ -z "${KEY_VAULT_NAME:-}" && "${RG}" == "stokai-tk" ]]; then
  KV="cdp-stokai-kv-prod"
else
  KV="${KEY_VAULT_NAME:-cdp-scrapers-kv-prod}"
fi
N8N_APP="${N8N_APP_NAME:-cdp-n8n-prod}"
SCRAPER_SITES="${CDP_SCRAPER_SITES:-gm,ml,vw,eu,melibox}"

if [[ -z "${SCRAPER_APPS:-}" ]]; then
  if [[ "${RG}" == "stokai-tk" ]]; then
    SCRAPER_APPS="cdp-stokai-scrapers-worker-prod cdp-stokai-scrapers-api-prod"
  else
    SCRAPER_APPS="cdp-scrapers-worker-prod cdp-scrapers-api-prod cdp-scrapers-worker-dev cdp-scrapers-api-dev"
  fi
fi
WORKER_APP_NAME="${WORKER_APP_NAME:-${SCRAPER_APPS%% *}}"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Missing ${ENV_FILE}" >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "${ENV_FILE}"
set +a

PROXY_JSON="${PROXY_URLS:-}"
if [[ -z "${PROXY_JSON}" || "${PROXY_JSON}" == "[]" ]]; then
  echo "PROXY_URLS empty in ${ENV_FILE}" >&2
  exit 1
fi

if [[ -z "${CREDENTIAL_MELIBOX_USER:-}" || -z "${CREDENTIAL_MELIBOX_PASS:-}" ]]; then
  echo "Set CREDENTIAL_MELIBOX_USER and CREDENTIAL_MELIBOX_PASS in ${ENV_FILE}" >&2
  exit 1
fi

patch_scraper_app() {
  local app="$1"
  echo "==> ${app}: secrets"
  az containerapp secret set -g "${RG}" -n "${app}" --secrets \
    "proxy-urls=${PROXY_JSON}" \
    "melibox-user=${CREDENTIAL_MELIBOX_USER}" \
    "melibox-pass=${CREDENTIAL_MELIBOX_PASS}" \
    --output none

  local extra_env=()
  if [[ "${app}" == *-worker-* ]]; then
    extra_env+=(
      "MAX_CONCURRENT_SCRAPERS=1"
      "SCRAPE_SITES_SEQUENTIAL=true"
    )
  fi

  echo "==> ${app}: env"
  az containerapp update -g "${RG}" -n "${app}" --set-env-vars \
    "PROXY_ROTATION_ENABLED=true" \
    "PROXY_FAIL_CLOSED=true" \
    "PROXY_AFFINITY_ENABLED=false" \
    "PROXY_STRICT_ALTERNATION=true" \
    "PROXY_ROTATE_CONTEXT_PER_SEARCH=true" \
    "PROXY_STATE_PER_IDENTITY=true" \
    "MELIBOX_ROTATE_CONTEXT_PER_SKU=false" \
    "${extra_env[@]}" \
    --output none
}

echo "==> Key Vault ${KV} (best-effort)"
if az keyvault secret set --vault-name "${KV}" --name proxy-urls --value "${PROXY_JSON}" --output none 2>/dev/null; then
  az keyvault secret set --vault-name "${KV}" --name melibox-user --value "${CREDENTIAL_MELIBOX_USER}" --output none
  az keyvault secret set --vault-name "${KV}" --name melibox-pass --value "${CREDENTIAL_MELIBOX_PASS}" --output none
  echo "    Key Vault updated."
else
  echo "    Skipped Key Vault (no write access). Container App secrets were still applied."
fi

for app in ${SCRAPER_APPS}; do
  if az containerapp show -g "${RG}" -n "${app}" --output none 2>/dev/null; then
    patch_scraper_app "${app}"
  fi
done

if az containerapp show -g "${RG}" -n "${N8N_APP}" --output none 2>/dev/null; then
  echo "==> n8n ${N8N_APP}: CDP_SCRAPER_SITES=${SCRAPER_SITES}"
  az containerapp update -g "${RG}" -n "${N8N_APP}" --set-env-vars \
    "CDP_SCRAPER_SITES=${SCRAPER_SITES}" \
    --output none
else
  echo "==> n8n ${N8N_APP}: skipped (not in ${RG})"
fi

OUT_IP="$(az containerapp show -g "${RG}" -n "${WORKER_APP_NAME}" \
  --query 'properties.outboundIpAddresses[0]' -o tsv 2>/dev/null || true)"
echo ""
echo "Done. Whitelist this IP in IPRoyal (ISP → Whitelisted IPs): ${OUT_IP:-unknown}"
echo "Local validation: cd scrapers && uv run python scripts/proxy_readiness_check.py --from-env"
echo "Prod smoke: API job with sites=[\"melibox\"] and force_refresh=true"
