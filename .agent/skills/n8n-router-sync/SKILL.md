---
name: n8n-router-sync
description: Edit, inject, validate, and publish CDP platform n8n workflows, including cdp_router, cdp_scraper, cdp_stokapi, cdp_progress, cdp_notifier, and DEV workflow copies.
---

# Skill: Sync CDP n8n workflows (platform)

Use when editing **router** logic, syncing platform workflows, or validating
dual-pipeline dispatch.

## Prerequisites

Read:

- `.agent/boundaries/n8n.md`
- `docs/n8n/LIVE_WORKFLOWS.md`
- `docs/architecture/DUAL_PIPELINE.md`

## Source of truth

| Artifact | Path |
|----------|------|
| Router Code | `n8n/src/*.js` |
| Router JSON | `n8n/workflows/cdp_router.json` |
| Scraper receiver | `n8n/workflows/cdp_scraper.json` |
| StokAPI receiver | `n8n/workflows/cdp_stokapi.json` |
| Progress workflow | `n8n/workflows/cdp_progress.json` |
| Notifier workflow | `n8n/workflows/cdp_notifier.json` |
| DEV copies | `n8n/workflows/dev/*.json` |

## Workflow

### 1. Edit router logic

Change only files under `n8n/src/`. Do not edit injected Code inside JSON by hand unless emergency — re-run inject after.

### 2. Inject into JSON

```bash
cd cdp-app
python3 scripts/sync_workflow_code_from_shared.py
```

Verify `cdp_router.json` contains updated Code node bodies.

### 3. Validate locally

```bash
node -e "
const fs = require('fs');
for (const f of [
  'n8n/workflows/cdp_router.json',
  'n8n/workflows/cdp_scraper.json',
  'n8n/workflows/cdp_stokapi.json',
  'n8n/workflows/cdp_progress.json',
  'n8n/workflows/cdp_notifier.json',
]) JSON.parse(fs.readFileSync(f,'utf8'));
console.log('JSON ok');
"
```

### 4. Contract checks (router)

- Scraper arm: `POST …/api/v1/jobs`, `force_refresh: false`, sites `gm,ml,vw,eu,pecadireta`
- StokAPI arm: `POST …/api/v1/muvstok/jobs`, callback `…/webhook/muvstok-result`
- Query params include `batch_group_id`, `dual_run` (`scraper` | `stokapi`)
- No Execute Workflow node targeting StokAPI

### 5. Push to n8n (user approval required)

**Code-only changes** (after inject):

```bash
make sync-n8n
```

This injects JSON, validates SDKs, pushes the full graph via n8n REST API (`scripts/n8n_publish.py`), and MCP-publishes. Set `CDP_PROGRESS_WORKFLOW_ID` to include `cdp_progress`.
Set `CDP_NOTIFIER_WORKFLOW_ID` to include `cdp_notifier`.

For surgical graph edits without full JSON replace, use MCP `update_workflow` `operations` + `publish_workflow` (see `docs/n8n/LIVE_WORKFLOWS.md`).

**DEV copies:** use `make n8n-dev-workflows` to regenerate
`n8n/workflows/dev/`, then `make sync-n8n-dev` with `CDP_DEV_*_WORKFLOW_ID`
exported.

## After sync

- Update `.agent/memory/implementation-state.md` if IDs or behavior changed
- Update `docs/n8n/LIVE_WORKFLOWS.md` if IDs changed
- Notify user of publish result; do not claim success without MCP confirmation

## Escalate to service tier

| Change | Delegate to |
|--------|-------------|
| Scraper callback flatten / sheets columns | `scrapers/.agent/skills/n8n-audit/SKILL.md` |
| StokAPI callback / sheets | `muvstok-api/n8n/docs/MUVSTOK_N8N_WORKFLOW_GUIDE.md` |
| Google Sheets dashboard semantics | `.agent/skills/google-sheets-dashboard/SKILL.md` |
| API request/response schema | Respective service `src/` or `app/` |
