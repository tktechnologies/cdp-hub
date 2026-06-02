# sync-n8n

**Purpose:** Inject router JS into workflow JSON and push to live n8n.

**Prerequisites:** `N8N_API_KEY` + `N8N_MCP_AUTH_HEADER` in `~/.cursor/mcp.json`, user approval for publish.

```bash
make sync-n8n
```

**Steps:** `scripts/sync_workflow_code_from_shared.py` → receiver patches → SDK validate → `scripts/n8n_publish.py` (REST PUT graph) → MCP `publish_workflow`.

**Pushes:** `cdp_router`, `cdp_scraper`, `cdp_stokapi`, and `cdp_progress` when `CDP_PROGRESS_WORKFLOW_ID` is set.

**Safety:** Never run publish without explicit user approval.
