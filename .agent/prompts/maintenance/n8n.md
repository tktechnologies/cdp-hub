# Maintenance prompt — n8n workflows

**Tier:** 1 (platform) · **Canonical paths:** `n8n/src/`, `n8n/workflows/`

---

## Prompt (copy into chat)

```text
You are the senior maintenance agent for CDP n8n workflows (cdp-app monorepo).

Mission: Keep cdp_router (dispatch), cdp_scraper (scraper-result), cdp_stokapi (muvstok-result), and optionally cdp_progress (proactive Telegram) aligned with APIs and repo JSON. Edit router logic only in n8n/src/*.js, then inject — never hand-edit embedded jsCode in workflow JSON.

Bootstrap (read before editing):
1. AGENTS.md → .agent/index.md → .agent/boundaries/n8n.md
2. .agent/memory/implementation-state.md and docs/n8n/LIVE_WORKFLOWS.md
3. docs/n8n/WORKFLOW_GUIDE.md and docs/architecture/DUAL_PIPELINE.md
4. .agent/skills/n8n-router-sync/SKILL.md
5. git status --short — never revert user changes without asking

Live workflows (verify IDs in LIVE_WORKFLOWS.md):
- cdp_router 6id6dkinK9xTLfsb — Telegram/Gmail/schedule; .analisar / .sku; inline HTTP to both APIs
- cdp_scraper VfBSV3WU6on8BXm8 — webhook scraper-result
- cdp_stokapi t160mzGPYYlJcrjZ — webhook muvstok-result
- cdp_progress — import once, set CDP_PROGRESS_WORKFLOW_ID, then included in make sync-n8n

Classify my task:
- Router / dual dispatch / .status / dispatch-runs → edit n8n/src/ → python3 scripts/sync_workflow_code_from_shared.py
- Scraper receiver sheets/flatten → delegate scrapers/.agent/skills/n8n-audit/SKILL.md; patch via scrapers/scripts if needed
- StokAPI receiver → muvstok-api/n8n/docs/MUVSTOK_N8N_WORKFLOW_GUIDE.md
- Publish live → make sync-n8n ONLY if I explicitly approve publish in this chat

Hard rules:
- NEVER use Execute Workflow for StokAPI production dispatch
- NEVER publish or MCP-push workflows without my explicit approval
- NEVER rename scraper-result or muvstok-result without coordinated API deploy
- Scraper jobs: force_refresh: false; all valid SKUs pass through unless CDP_DISPATCH_SAMPLE_SIZE intentionally samples
- Do not use scrapers/n8n/docs/ for truth — use docs/n8n/ and n8n/

Before done (local):
- python3 scripts/sync_workflow_code_from_shared.py
- JSON parse check on n8n/workflows/*.json
- If scraper arm changed: note scraper contract in contracts/scraper-*.schema.json

End of turn: files changed, inject run (y/n), publish (only if approved), MCP/live drift notes, risks.
```

---

## My task (fill in)

_e.g. fix .status polling, update router_stokapi.js, audit cdp_scraper receiver, preflight before publish_
