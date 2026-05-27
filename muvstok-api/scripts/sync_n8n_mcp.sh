#!/usr/bin/env bash
# Push Muvstok workflows to live n8n via Cursor MCP (no N8N_API_KEY required).
# Run from repo root in a shell where user-n8n-mcp is enabled, or ask the agent to run MCP update_workflow.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
echo "MCP sync (from repo root):"
echo "  python3 scripts/generate_sender_sdk.py"
echo "  python3 scripts/sync_n8n_via_mcp_http.py"
echo ""
echo "Or Cursor MCP: validate_workflow → update_workflow → publish_workflow"
echo ""
echo "REST fallback (needs N8N_API_KEY from n8n UI):"
echo "  source scripts/export_n8n_env.sh && python3 scripts/sync_n8n_workflows.py"
