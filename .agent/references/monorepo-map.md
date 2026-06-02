# CDP Monorepo Map

**Updated:** 2026-06-01

```text
cdp-app/
├── .agent/                 # Platform agent workspace (Tier 1)
│   ├── rules/              # Task-scoped agent rules
│   ├── knowledge/          # Cross-service ownership and sync maps
│   ├── memory/             # Durable project state and decisions
│   ├── references/         # Knowledge maps
│   ├── commands/           # Repeatable command recipes
│   ├── prompts/            # Startup and maintenance prompts
│   ├── skills/             # Reusable platform workflows
│   └── sub-agents/         # Delegation briefs
├── docs/                   # Cross-cutting documentation
├── n8n/
│   ├── src/                # Router Code source (12 JS files)
│   ├── lib/                # Receiver helpers
│   ├── workflows/          # cdp_router, cdp_scraper, cdp_stokapi, cdp_progress JSON
│   └── settings/
├── contracts/              # JSON Schema shared contracts
├── scripts/
│   ├── sync_workflow_code_from_shared.py
│   └── sync-all-n8n.sh
├── scrapers/               # Scraper service (Tier 2a)
│   ├── src/
│   ├── tests/
│   ├── alembic/
│   ├── infra/              # Azure Bicep
│   └── .agent/
├── muvstok-api/            # StokAPI (Tier 2b)
│   ├── app/
│   ├── specs/
│   └── .agent/
├── docker-compose.yml      # Shared postgres + redis
└── Makefile
```

## Key paths

| Task | Path |
|------|------|
| Edit router Code | `n8n/src/*.js` |
| Workflow JSON | `n8n/workflows/` |
| Sync to n8n | `make sync-n8n` |
| Scraper API | `scrapers/src/` |
| StokAPI API | `muvstok-api/app/` |
| Live workflow IDs | `docs/n8n/LIVE_WORKFLOWS.md` |
