#!/usr/bin/env bash
# Source before manual n8n REST use or scripts/n8n_publish.py from monorepo root.
set -euo pipefail

export N8N_BASE_URL="${N8N_BASE_URL:-https://automacao.tktechnologies.com.br}"

if [[ -z "${N8N_API_KEY:-}" ]]; then
  echo "N8N_API_KEY is not set." >&2
  echo "Create one in n8n: Settings → n8n API → Create API key" >&2
  echo "Then: export N8N_API_KEY='<key>'" >&2
  echo "Platform sync: cd ../.. && make sync-n8n (requires approval)" >&2
  return 1 2>/dev/null || exit 1
fi

echo "N8N_BASE_URL=$N8N_BASE_URL"
echo "N8N_API_KEY is set (${#N8N_API_KEY} chars)"
