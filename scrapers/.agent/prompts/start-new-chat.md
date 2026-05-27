# Start New Chat — CDP Scrapers

Use at the start of any fresh AI-agent chat for **scrapers** and scraper-adjacent n8n receiver work.

## Bootstrap

1. Read [.agent/index.md](../index.md) and [agent-startup.md](agent-startup.md)
2. Read `docs/MAINTENANCE_CHECKPOINT.md`
3. For router / dual pipeline (read-only unless platform task): `../../n8n/src/`, `../../.agent/skills/n8n-router-sync/SKILL.md`
4. `git status --short` — never revert user changes

## Dual pipeline (current)

| Arm | API | Receiver |
|-----|-----|----------|
| Scraper | `POST /api/v1/jobs` | `cdp_scraper` → `scraper-result` |
| StokAPI | `POST /api/v1/muvstok/jobs` (router inline HTTP) | `cdp_stokapi` → `muvstok-result` |

Production orchestration: **`cdp_router`** only (not legacy `cdp_analise`). See [../../docs/architecture/DUAL_PIPELINE.md](../../docs/architecture/DUAL_PIPELINE.md).

## Quality gates

```bash
make -C scrapers test lint
```

## End of turn

Update service memory and platform [implementation-state.md](../../.agent/memory/implementation-state.md) when live IDs or behavior change.
