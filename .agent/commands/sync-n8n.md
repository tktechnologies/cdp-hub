# sync-n8n

**Purpose:** Inject router JS into workflow JSON and push to live n8n.

**Prerequisites:** `N8N_API_KEY`, MCP access, user approval for publish.

```bash
make sync-n8n
```

**Steps:** `scripts/sync_workflow_code_from_shared.py` → optional receiver patches → SDK gen → MCP push.

**Pushes:** `cdp_router`, `cdp_scraper`, `cdp_stokapi`.

**Not pushed (manual):** `cdp_progress` — import `n8n/workflows/cdp_progress.json` in n8n UI, set `CDP_PROGRESS_*` env vars, activate. See [memory/implementation-state.md](../memory/implementation-state.md).

**Safety:** Never run publish without explicit user approval.
