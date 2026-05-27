# CDP agent architecture

**Updated:** 2026-05-26

How AI agents should navigate the CDP monorepo: **platform**, **service**, and **n8n** layers.

## Three tiers

```text
┌─────────────────────────────────────────────────────────────┐
│  Tier 1 — Platform (cdp-app/)                               │
│  .agent/  AGENTS.md  docs/ARCHITECTURE.md                    │
│  Owns: dual pipeline, n8n/src/, sync-all-n8n, boundaries │
└───────────────────────────┬─────────────────────────────────┘
                            │
         ┌──────────────────┴──────────────────┐
         ▼                                      ▼
┌─────────────────────┐            ┌─────────────────────┐
│ Tier 2a — Scraper   │            │ Tier 2b — StokAPI   │
│ scrapers/.agent/    │            │ muvstok-api/.agent/ │
│ + .agent/skills/    │            │ specs/ skills/      │
│ Owns: Playwright,   │            │ Owns: Redis Streams,│
│ Celery, cache,      │            │ Muvstok client,     │
│ cdp_scraper JSON    │            │ cdp_stokapi JSON    │
└──────────┬──────────┘            └──────────┬──────────┘
           │                                   │
           └──────────────┬────────────────────┘
                          ▼
              ┌───────────────────────┐
              │ Tier 3 — n8n contracts │
              │ 3 workflows, 2 webhooks │
              │ n8n/src → cdp_router  │
              └───────────────────────┘
```

## Where to start

| Your task | Start here |
|-----------|------------|
| Any cross-service or “whole CDP” work | [AGENTS.md](../../AGENTS.md) → [.agent/index.md](../../.agent/index.md) |
| Router, `.analisar`, dual dispatch, sync all workflows | Platform [.agent/skills/n8n-router-sync/SKILL.md](../../.agent/skills/n8n-router-sync/SKILL.md) |
| Scraper code, cache, Celery, Playwright | [scrapers/AGENTS.md](../../scrapers/AGENTS.md) |
| StokAPI jobs, worker, callbacks | [muvstok-api/AGENTS.md](../../muvstok-api/AGENTS.md) |
| Only receiver JSON (no router) | Service n8n path + platform boundaries |

## Ownership boundaries

| Concern | Owner | Do not |
|---------|-------|--------|
| `n8n/src/*.js` | Platform | Edit embedded Code in workflow JSON by hand |
| `cdp_router.json` | Platform sync → `n8n/workflows/` | Dispatch StokAPI via Execute Workflow |
| `cdp_scraper.json` | Scraper service | Change scraper API callback shape without updating `src/models/schemas.py` |
| `cdp_stokapi.json` | StokAPI service | Change Muvstok callback shape without updating `app/schemas/callbacks.py` |
| Scraper API `/api/v1/*` | Scraper | Add Muvstok logic to scraper repo |
| StokAPI `/api/v1/muvstok/*` | StokAPI | Add Playwright/scrape cache to muvstok repo |
| Live workflow publish | Platform skill + user approval | Auto-publish without explicit approval |

## n8n single pipeline of truth

```text
Edit:     cdp-app/n8n/src/*.js
Inject:   python3 scripts/sync_workflow_code_from_shared.py
          → n8n/workflows/cdp_router.json
SDK+push: make sync-n8n
          → cdp_router, cdp_scraper, cdp_stokapi
```

Receivers are owned by services but **published together** in one sync script.

## Agent workspaces

| Path | Role |
|------|------|
| `cdp-app/.agent/` | Platform index, rules, boundaries, n8n skills, implementation state |
| `scrapers/.agent/` | Scraper index, rules, memory, skills, commands |
| `muvstok-api/.agent/` | Full StokAPI workspace (skills, sub-agents, specs) |
| `cdp-app/.agent/workflows/` (top-level `*.md`) | AIOX IDE personas — **not** CDP runtime |
| `cdp-app/.agent/workflows/cdp/` | CDP platform workflows (n8n release, etc.) |

## Change checklist (any tier)

1. Identify tier — platform vs scraper vs stokapi vs n8n-only.
2. Read boundaries: `.agent/boundaries/services.md`, `.agent/boundaries/n8n.md`.
3. Implement in the **owning** directory only.
4. Update **same tier** memory (`implementation-state.md`) and human docs.
5. If n8n or cross-service: run inject script; `make sync-n8n` only with user approval.
6. Run service quality gates (`make -C scrapers test`, `make check-muvstok`).

## Best practices

- **Thin cross-repo coupling:** APIs talk via HTTP + webhooks only; no shared Python packages between services.
- **Stable webhook paths:** `scraper-result`, `muvstok-result` — rename only with coordinated deploy.
- **Cache vs live scrape:** Router always `force_refresh: false`; never bypass cache in router to “fix” stale data without understanding TTL.
- **Max 5 SKUs** per `.analisar` / `.sku` round — enforced in `router_limitar_skus.js`.
- **Secrets:** Key Vault → Container App env; never in workflow JSON or agent memory files.
- **Documentation:** Platform truth in `docs/`; service truth in service `docs/` + `.agent/memory/`; avoid duplicating full architecture in three places — link to canonical docs.
