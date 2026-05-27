# Dual .analisar — Scraper + Muvstok (2026-05-22)

Published via n8n MCP (`validate_workflow` → `update_workflow` → `publish_workflow`).

**Diagramas e reunião:** [CDP_DUAL_ANALISE_ARCHITECTURE.md](../CDP_DUAL_ANALISE_ARCHITECTURE.md) · [MEETING_DUAL_ANALISE_NOVA_ARQUITETURA.md](../meetings/MEETING_DUAL_ANALISE_NOVA_ARQUITETURA.md)

## Workflows

| Workflow | ID | Active version | Change |
|----------|-----|----------------|--------|
| `cdp_analise` | `6id6dkinK9xTLfsb` | `0e67a923-a6b9-4b12-9ea1-4dc4d4c8bc7b` | Inline `🚀 POST Muvstok API` router + `📱 Telegram: erro Muvstok` |
| `cdp_muvstok-api_starter` | `PXLHDzRbBVgs8Xl2` | `d4b91b2d-7bc9-49e8-8654-507247243ca9` | Manual only; fixed `={{` URL (was `={` after MCP) |

**Root cause (exec 470):** sub-workflow HTTP URL used `={$env...}` instead of `={{ $env... }}` → Invalid URL. Production `.analisar` now POSTs Muvstok inside `cdp_analise`.

## User flow

1. Telegram or email: `.analisar`
2. Start message: Scraper + Muvstok, 5 peças, 2 avisos ao concluir
3. Completion: `cdp_resultado` (scraper) + `cdp_muvstok-api_receiver` (estoque)

## Repo publish commands

```bash
# scrapers
node scripts/n8n_workflow_json_to_sdk.mjs n8n/workflows/cdp_analise.json --workflow-id=6id6dkinK9xTLfsb > n8n/sdk/cdp_analise.workflow.ts
python3 scripts/push_workflow_mcp.py --workflow-id=6id6dkinK9xTLfsb --sdk=n8n/sdk/cdp_analise.workflow.ts --description="dual analisar"

# muvstok-api
python3 scripts/generate_sender_sdk.py
python3 scripts/sync_n8n_via_mcp_http.py
```

## Smoke test

1. Send `.analisar` from allowed Telegram chat.
2. Confirm one start message mentions Scraper + Muvstok.
3. Check n8n executions for `cdp_analise` and `cdp_muvstok-api_starter`.
4. Wait for two completion notifications.
