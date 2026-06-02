# Skill: Sync CDP n8n workflows (platform)

Use when editing **router** logic, syncing all three production workflows, or validating dual-pipeline dispatch.

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

For surgical graph edits without full JSON replace, use MCP `update_workflow` `operations` + `publish_workflow` (see `docs/n8n/LIVE_WORKFLOWS.md`).

## After sync

- Update `.agent/memory/implementation-state.md` if IDs or behavior changed
- Update `docs/n8n/LIVE_WORKFLOWS.md` if IDs changed
- Notify user of publish result; do not claim success without MCP confirmation

## Escalate to service tier

| Change | Delegate to |
|--------|-------------|
| Scraper callback flatten / sheets columns | `scrapers/.agent/skills/n8n-audit/SKILL.md` |
| StokAPI callback / sheets | `muvstok-api/n8n/docs/MUVSTOK_N8N_WORKFLOW_GUIDE.md` |
| API request/response schema | Respective service `src/` or `app/` |
