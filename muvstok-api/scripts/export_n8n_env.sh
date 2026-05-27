#!/usr/bin/env bash
# Source before sync_n8n_workflows.py (REST) or manual n8n CLI use.
# MCP deploy uses ~/.cursor/mcp.json (separate token) — see scripts/sync_n8n_mcp.sh
set -euo pipefail

export N8N_BASE_URL="${N8N_BASE_URL:-https://automacao.tktechnologies.com.br}"

if [[ -z "${N8N_API_KEY:-}" ]]; then
  echo "N8N_API_KEY is not set." >&2
  echo "Create one in n8n: Settings → n8n API → Create API key" >&2
  echo "Then: export N8N_API_KEY='<key>'" >&2
  echo "Or run: ./scripts/sync_n8n_mcp.sh (uses Cursor n8n MCP, no REST key)" >&2
  return 1 2>/dev/null || exit 1
fi

echo "N8N_BASE_URL=$N8N_BASE_URL"
echo "N8N_API_KEY is set (${#N8N_API_KEY} chars)"
