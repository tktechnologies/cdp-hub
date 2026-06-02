# n8n Rules

**Applies to:** `n8n/**`, router Code, and workflow JSON.

## Source of truth

- Router Code: `n8n/src/*.js`
- Workflow JSON: `n8n/workflows/*.json`
- Receiver helpers: `n8n/lib/`

## Sync

```bash
python3 scripts/sync_workflow_code_from_shared.py
make sync-n8n
```

`make sync-n8n` publishes live workflows and requires explicit user approval.

## Do not

- Edit embedded `jsCode` in workflow JSON by hand.
- Publish live workflows without explicit approval.
- Use deprecated workflows: `cdp_analise`, `cdp_resultado`, `cdp_muvstok-api_starter`, `muvstok_job_sender`, or `muvstok_job_receiver`.
