#!/usr/bin/env bash
# Push platform n8n workflows from the monorepo root (no service-local sync scripts).
set -euo pipefail
MONOREPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
echo "n8n sync (from monorepo root):"
echo "  cd $MONOREPO_ROOT"
echo "  python3 scripts/sync_workflow_code_from_shared.py"
echo "  make sync-n8n          # requires explicit approval; uses scripts/n8n_publish.py"
echo ""
echo "Or Cursor MCP: validate_workflow → update_workflow → publish_workflow"
echo "See docs/n8n/LIVE_WORKFLOWS.md and .agent/skills/n8n-router-sync/SKILL.md"
