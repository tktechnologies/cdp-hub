# sync-n8n

**Purpose:** Inject router JS into workflow JSON and push to live n8n.

**Prerequisites:** n8n API credentials available through env or approved local
config, workflow IDs exported for optional workflows, and user approval for
publish.

```bash
make sync-n8n
```

**Steps:** `scripts/sync_workflow_code_from_shared.py` → receiver patches → SDK validate → `scripts/n8n_publish.py` (REST PUT graph) → MCP `publish_workflow`.

**Pushes:** `cdp_router`, `cdp_scraper`, `cdp_stokapi`, plus `cdp_progress`
when `CDP_PROGRESS_WORKFLOW_ID` is set and `cdp_notifier` when
`CDP_NOTIFIER_WORKFLOW_ID` is set.

**DEV copies:** `make n8n-dev-workflows` regenerates
`n8n/workflows/dev/*.json`; `make sync-n8n-dev` pushes them when
`CDP_DEV_*_WORKFLOW_ID` values are exported.

**Safety:** Never run publish without explicit user approval.
