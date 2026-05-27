# CDP Platform — Agent Index

**Tier 1.** For service-deep work, descend to Tier 2 (see [docs/architecture/AGENT_ARCHITECTURE.md](../docs/architecture/AGENT_ARCHITECTURE.md)).

## Decision tree

```text
Does the task touch n8n/src, cdp_router dispatch, or all 3 workflows?
  YES → Stay here (platform tier)
  NO  → Is it scraper code/cache/Playwright?
          YES → scrapers/.agent/index.md
          NO  → Is it StokAPI/worker/Muvstok?
                  YES → muvstok-api/.agent/index.md
```

## Always read first (platform)

1. [../AGENTS.md](../AGENTS.md)
2. [../docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md)
3. [../docs/architecture/AGENT_ARCHITECTURE.md](../docs/architecture/AGENT_ARCHITECTURE.md)
4. [../docs/architecture/DUAL_PIPELINE.md](../docs/architecture/DUAL_PIPELINE.md)
5. [../docs/n8n/LIVE_WORKFLOWS.md](../docs/n8n/LIVE_WORKFLOWS.md)
6. [memory/implementation-state.md](memory/implementation-state.md)
7. [boundaries/n8n.md](boundaries/n8n.md)

## Platform task routing

| Task | Skill / path |
|------|----------------|
| Edit router, inject, sync/publish n8n | [skills/n8n-router-sync/SKILL.md](skills/n8n-router-sync/SKILL.md) |
| Change `.analisar` / `.sku` / dual behavior | [skills/dual-pipeline-change/SKILL.md](skills/dual-pipeline-change/SKILL.md) |
| Progress visibility (`.status`, `cdp_progress`, dispatch-runs API) | [memory/implementation-state.md](memory/implementation-state.md) |
| n8n release checklist | [workflows/cdp/n8n-release-checklist.md](workflows/cdp/n8n-release-checklist.md) |
| Fresh platform chat | [prompts/platform-startup.md](prompts/platform-startup.md) |
| Maintenance prompts (by type) | [prompts/maintenance/README.md](prompts/maintenance/README.md) |
| Service boundaries | [boundaries/services.md](boundaries/services.md) |

## Delegate to Tier 2

| Task | Workspace |
|------|-----------|
| Scraper API, Celery, cache, Playwright, `cdp_scraper` receiver logic | [scrapers/.agent/index.md](../scrapers/.agent/index.md) |
| StokAPI API, Redis worker, `cdp_stokapi` receiver | [muvstok-api/.agent/index.md](../muvstok-api/.agent/index.md) |

## Completion (platform)

- Router: `python3 scripts/sync_workflow_code_from_shared.py` before any router JSON commit
- Publish: `make sync-n8n` only with user approval
- Update [memory/implementation-state.md](memory/implementation-state.md) and service memory if facts changed
- Run service gates if you touched service code
