---
name: dual-pipeline-change
description: Change CDP .analisar, .sku, dual dispatch, progress, status, batch metadata, or cross-service router behavior across Scraper and API Diversos.
---

# Skill: Change dual pipeline behavior

Use when modifying `.analisar`, `.sku`, parallel dispatch, batch limits, or cross-service metadata.

## Read first

1. `docs/architecture/DUAL_PIPELINE.md`
2. `docs/architecture/AGENT_ARCHITECTURE.md`
3. `.agent/boundaries/services.md`

## Typical change map

| User-visible change | Files to touch |
|---------------------|----------------|
| SKU pass-through / optional sampling | `n8n/src/router_limitar_skus.js` (`CDP_DISPATCH_SAMPLE_SIZE`, default 0 = all) |
| Scraper sites / cache bypass | `n8n/src/formatar_payload_scraper.js` + possibly `scrapers/src/services/orchestrator.py` |
| StokAPI callback query params | `n8n/src/router_stokapi.js` + `muvstok-api/app/schemas/` |
| Sheet PROCESSADO timing | `n8n/src/emparelhar_scraper.js` |
| Receiver sheets/Telegram | Service workflow JSON only |
| Aggregate final notification | `cdp_notifier` workflow + receiver handoff patches |

## Parallelism model

Both arms fire from **one** router execution. They are independent HTTP jobs:

- Different `job_id` / `batch_group_id` links them in metadata
- Receiver callbacks arrive independently and write Sheets
- User-facing final delivery is aggregated by `cdp_notifier` when
  `delivery_mode: aggregate`
- Do not block Scraper on StokAPI or vice versa in n8n

## Testing

```bash
make smoke-cache   # from monorepo root, if script covers your change
```

Manual: Telegram `.sku TESTSKU` and verify both sheet updates + two notifications.

## Sync

After router JS changes: follow `n8n-router-sync` skill.
