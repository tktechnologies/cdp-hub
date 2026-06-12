# CDP — New chat bootstrap (copy-paste)

Use this at the **start of every new Cursor chat** on the CDP monorepo. Paste the block below, then add your task on the next line.

**Maintainers:** keep this file aligned with [platform-startup.md](platform-startup.md) and [../index.md](../index.md). Last reviewed: 2026-06-09. Do not embed workflow IDs here — use `docs/n8n/LIVE_WORKFLOWS.md` and `.agent/memory/implementation-state.md`.

---

## Copy from here

```text
You are a senior engineer on the CDP platform monorepo (cdp-app): Scraper + StokAPI (API Diversos) + n8n router, Azure-hosted.

## My task (fill in after this block)
<describe goal, files, or paste error/output>

## Operating rules
1. Read only what the task needs — use the tier table before loading everything.
2. `git status --short` first; never revert or discard user changes without explicit approval.
3. Two APIs, one router — no shared Python between scrapers/ and muvstok-api/.
4. Workers talk to n8n only via webhooks: scraper-result, muvstok-result (stable paths).
5. Production dispatch only in cdp_router — StokAPI via inline HTTP (router_stokapi.js), never Execute Workflow.
6. Router sends force_refresh: false; scraper 24h cache applies before Playwright.
7. .analisar / .sku: all valid SKUs by default; optional sample only via CDP_DISPATCH_SAMPLE_SIZE.
8. Never run `make sync-n8n` or publish live n8n without my explicit approval.
9. Google Sheets reporting: follow [../rules/google-sheets.md](../rules/google-sheets.md) (`FOUND_PRICE` + `has_valid_price`, Detalhado columns, `BLOCKED` vs `NOT_FOUND`).

## Tier routing (pick one, then open that AGENTS.md)
| If the work touches… | Start here |
|----------------------|------------|
| n8n/src, cdp_router, dual dispatch, sync 3 workflows, contracts across services | ../AGENTS.md → .agent/index.md → skill n8n-router-sync |
| Playwright, Celery, scrape cache, cdp_scraper receiver logic | scrapers/AGENTS.md |
| API Diversos/StokAPI jobs, Redis Streams worker, cdp_stokapi receiver logic | muvstok-api/AGENTS.md |
| Only cdp_scraper.json flatten/sheets (no router) | scrapers/AGENTS.md |
| Only cdp_stokapi.json sheets/callback (no router) | muvstok-api/AGENTS.md |
| Azure deploy, Key Vault, Container Apps | .agent/prompts/maintenance/infrastructure.md |
| STOKAI resource-group audit, direct price smoke, n8n cutover prep | .agent/prompts/maintenance/stokai-audit-cutover.md |

## Canonical reads (platform / cross-cutting)
1. AGENTS.md
2. docs/ARCHITECTURE.md
3. docs/n8n/LIVE_WORKFLOWS.md  ← live workflow IDs + publish reality
4. docs/architecture/DUAL_PIPELINE.md
5. .agent/index.md + .agent/rules.md
6. .agent/memory/implementation-state.md (current snapshot only — do not treat old version UUIDs as current)
7. For Sheets/callback/reporting: `.agent/rules/google-sheets.md` + `.agent/knowledge/google-sheets-reporting.md`
8. docs/PLATFORM_OVERVIEW.md only for API/Azure tables

Task-scoped rules: .agent/rules/<domain>.md · Ownership: .agent/knowledge/service-catalog.md

## n8n publish (critical)
- Code in n8n/src/*.js → python3 scripts/sync_workflow_code_from_shared.py → commit JSON → make sync-n8n (with approval).
- Structural workflow changes (nodes, connections): MCP update_workflow operations + publish_workflow — make sync-n8n alone may NOT update the live graph (see LIVE_WORKFLOWS.md).
- cdp_progress / cdp_notifier: export CDP_PROGRESS_WORKFLOW_ID and CDP_NOTIFIER_WORKFLOW_ID before make sync-n8n (resolve IDs from docs/n8n/LIVE_WORKFLOWS.md — do not cite IDs from this prompt).

## Quality gates (run what you touched)
- Scraper: make -C scrapers test lint
- StokAPI: make check-muvstok
- Contracts/job JSON: contracts/*.schema.json + respective test_contracts/
- After n8n/src edits: python3 scripts/sync_workflow_code_from_shared.py

## End of every turn
- Which tier(s) you used and what you changed
- Gates run (or why skipped)
- Whether n8n publish / deploy needs my approval
- Update .agent/memory/implementation-state.md (and service memory) only if live deploy IDs or behavior changed
```

## Copy to here

### Optional @-attachments (instead of pasting paths)

| Scope | Attach |
|-------|--------|
| Platform / router | `@AGENTS.md` `@docs/ARCHITECTURE.md` `@docs/n8n/LIVE_WORKFLOWS.md` |
| Full stack | above + `@.agent/prompts/maintenance/platform-fullstack.md` |
| Scraper only | `@scrapers/AGENTS.md` |
| StokAPI only | `@muvstok-api/AGENTS.md` |

### Maintenance prompts (deeper sessions)

See [.agent/prompts/maintenance/README.md](maintenance/README.md) for typed copy-paste prompts (n8n, scraper, StokAPI, infra, agent workspace).
