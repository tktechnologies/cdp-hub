# Production Audit — Muvstok n8n + API Pipeline

> **Superseded in part (2026-05-27):** Production dispatch uses monorepo `cdp_router` + `cdp_stokapi` (`../../n8n/workflows/`). Removed: `muvstok_job_sender.json`, standalone sender workflow. Sync: `make sync-n8n` from monorepo root. Canonical IDs: [docs/n8n/LIVE_WORKFLOWS.md](../../docs/n8n/LIVE_WORKFLOWS.md).

Last run: **2026-05-21** (live production checks included below).

## Scope

Validate the full path for ~1k SKUs in Google Sheets (`cdp_skus`) through n8n → Azure API → Redis queue → worker (1 SKU at a time) → PostgreSQL → callback → n8n receiver → results sheets + Telegram.

**Safe audit size:** 5 SKUs (random sample from unprocessed rows). Do **not** run the full sheet until this checklist is green.

---

## Architecture (reference)

```text
cdp_skus (Google Sheets)
  → n8n sender (DQ, batch, POST jobs)
  → cdp-muv-api POST /api/v1/muvstok/jobs
  → Redis stream muvstok:jobs
  → cdp-muv-worker (sequential SKU processing)
  → PostgreSQL (muvstok_jobs, items, snapshots, api_data)
  → POST webhook/muvstok-result (x-webhook-secret)
  → n8n receiver → cdp_resultados + cdp_skus update + Telegram
```

---

## Pre-flight (before any SKU run)

| # | Check | Command / where | Pass criteria |
|---|--------|-----------------|---------------|
| 1 | API health | `curl $BASE/api/v1/muvstok/health` | `{"status":"ok"}` HTTP 200 |
| 2 | API replicas | `az containerapp show -n cdp-muv-api -g automation` | minReplicas ≥ 1, FQDN reachable |
| 3 | Worker running | `az containerapp show -n cdp-muv-worker -g automation` | `runningStatus: Running` |
| 4 | n8n receiver active | n8n UI / MCP `get_workflow_details` `t160mzGPYYlJcrjZ` | Active + published |
| 5 | n8n sender inactive | `PXLHDzRbBVgs8Xl2` | Manual trigger only (no accidental full sheet) |
| 6 | Secrets aligned | Key Vault `cdp-scrapers-kv-prod` → `cdp-n8n-prod` + `cdp-muv-api` | API key + callback secret match across n8n/API |
| 7 | Live workflow sync | `python scripts/sync_n8n_workflows.py --all` | Repo JSON matches n8n after changes |
| 8 | Redis stream | `XLEN muvstok:jobs`, `XPENDING` | No huge pending backlog before audit |
| 9 | Dead letter | `XLEN muvstok:jobs:dead-letter` | Review ~130 historical DLQ; requeue or purge per ops |

---

## 5-SKU audit procedure

### Option A — n8n (sheet-driven, recommended for Excel + Sheets proof)

1. On `cdp-n8n-prod`, set for **one** manual run:
   - `CDP_MUVSTOK_AUDIT_SAMPLE=5` — random 5 unprocessed SKUs (after DQ)
   - **or** `CDP_MUVSTOK_MAX_SKUS=5` — first 5 unprocessed SKUs (deterministic)
   - `CDP_MUVSTOK_BATCH_SIZE=5` — single job batch
2. Confirm dispatch is via `cdp_router` inline HTTP (not a separate sender workflow). Receiver: `../../n8n/workflows/cdp_stokapi.json`.
3. Run **sender** manually once.
4. Record: execution ID, `job_id`(s) from POST node, rows marked `processando...` on `cdp_skus`.

### Option B — API script (no Sheets read; good for API/DB/Redis/callback)

```bash
cd muvstok-api
source .env
# Pass 5 real SKUs from your sheet (replace placeholders)
uv run python scripts/production_audit.py \
  --skus "SKU1,SKU2,SKU3,SKU4,SKU5" \
  --source prod-audit-manual
```

Polls job status, prints per-SKU results and callback state.

---

## Verification matrix (per audit run)

| Layer | What to verify | Evidence |
|-------|----------------|----------|
| **Request contract** | `skus`, `callback_url`, `metadata`, optional `idempotency_key` | POST body in n8n execution; API 202 + `job_id` |
| **Auth** | `X-API-Key` on jobs; invalid key → 401 | curl with/without key |
| **Callback URL** | Public HTTPS only (no localhost) | `app/core/security.py` `is_public_callback_url` |
| **Idempotency** | Same key → same `job_id`, no duplicate queue | Re-POST with same `idempotency_key` |
| **Redis queue** | Message on `muvstok:jobs` after accept | API log `job_published_to_redis`; `queue_messages.redis_message_id` |
| **Anti-bot / rate** | **One Muvstok HTTP call per SKU**, sequential in worker | `JobProcessor` loop; worker logs show SKU order; no parallel SKU fetches in one job |
| **Token cache** | Key Vault token reuse; refresh on 401/403 | Worker logs `job_completed` without auth storm |
| **DB — job** | `muvstok_jobs` status, counts, `callback_status` | `GET /jobs/{id}` or SQL |
| **DB — items** | 1 row per SKU, status + `last_error_code` | `muvstok_job_items` |
| **DB — raw** | `muvstok_raw_snapshots` for succeeded SKUs | count = succeeded count |
| **DB — normalized** | `muvstok_api_data` per SKU | `response_status` succeeded / not_found / failed |
| **Callback** | `x-webhook-secret`, payload shape | n8n receiver execution **success**; `callback_deliveries` |
| **Sheets — source** | `PROCESSADO` → processing then `✅ Processado`; `ENCONTRADO` | Visual check on sampled rows |
| **Sheets — results** | Rows in **Detalhado** / **Historico** | `cdp_resultados` spreadsheet |
| **Telegram** | Summary if `notify=telegram` | Message in configured chat |
| **Governance** | Consistency rules on payload | See gaps below |

---

## Live audit snapshot (2026-05-21)

Script/API probe (5 SKUs: 2 known + 3 fake for not_found path):

| Step | Result | Evidence |
|------|--------|----------|
| API health | **Pass** | HTTP 200 `{"status":"ok"}` |
| Job accepted | **Pass** | `job_id` `3d9ed9cb-c8d9-4a8c-96f6-e8bb6a9d4013` |
| Worker processing | **Pass** | Status `processing` → terminal ~25s |
| SKU outcomes | **Pass** | 2 succeeded (`7703062062`, `661003M6M00ZZ`), 3 `not_found` |
| Callback | **Pass** | `callback_status: succeeded` |
| n8n receiver | **Pass** | Execution **362** `success` (webhook) |
| Partial success | **Pass** | Job `partially_succeeded` (valid per spec) |

---

## Findings and gaps

### Working as designed

- Sequential SKU processing inside each job (`for item in items` in `JobProcessor`).
- Worker reads **one Redis message at a time** (`read_jobs(count=1)`).
- Per-SKU DB commit after processing (restart-safe).
- Callback retries (up to `callback_max_attempts`); raw data kept if callback fails.
- Webhook secret on outbound callback.
- n8n DQ: dedupe, skip processed, min SKU length.

### Gaps / risks (prioritize before 1k SKU run)

| Risk | Severity | Detail | Mitigation |
|------|----------|--------|------------|
| **Parallel jobs at scale** | High | n8n sends batches of 50; ~20 jobs for 1k SKUs → up to 2 workers × concurrent jobs = many parallel Muvstok calls | Set `CDP_MUVSTOK_BATCH_SIZE=1` or `5` for rollout; scale worker `maxReplicas=1` during soak; add inter-SKU delay in worker if Muvstok throttles |
| **No response cache (v1)** | Medium | Every SKU hits Muvstok API; `POST /lookup` not implemented | Add snapshot lookup + TTL before bulk; use `muvstok_api_data` for re-runs |
| **GovernanceService stub** | Medium | `governance_service.py` empty — no automated consistency rules | Implement checks: price &gt; 0, required fields, branch dedupe |
| **JSON vs SDK sender drift** | Medium | Repo JSON missing `CDP_MUVSTOK_MAX_SKUS` / `AUDIT_SAMPLE` in DQ node; SDK has MAX_SKUS | Run `sync_n8n_workflows.py` after aligning JSON/SDK |
| **Sheet column mismatch** | Medium | DQ reads `CODIGO`; update node writes `SKU` + `row_number` | Confirm sheet headers; align to one column name |
| **Dead-letter backlog** | Medium | ~130 jobs during worker bring-up | Requeue script or ops runbook |
| **WSL → PostgreSQL** | Low | Direct `psql` may timeout | Use `production_audit.py` via API or `az containerapp exec` |
| **Full sheet without cap** | Critical | Accidental manual run on 1k rows | Keep sender inactive; use `CDP_MUVSTOK_AUDIT_SAMPLE=5` or `MAX_SKUS` |

### Cache clarification

| Cache | Exists? | Location |
|-------|---------|----------|
| Muvstok API response (SKU) | **No** (v1) | N/A — always live fetch |
| Auth token | **Yes** | Key Vault secret `muvstok-api-token` when KV configured; else in-memory per worker run |
| Job queue | **Yes** | Redis `muvstok:jobs` |
| Scraper price cache | **Separate** | `product_price_snapshots` (scraper pipeline; not wired in Muvstok worker) |

---

## Security checklist

- [ ] API keys only in Key Vault / Container App secrets (never in git)
- [ ] `CALLBACK_WEBHOOK_SECRET` matches n8n `CDP_MUVSTOK_CALLBACK_WEBHOOK_SECRET`
- [ ] Callback URLs are HTTPS and not internal IPs
- [ ] Logs exclude tokens, passwords, full `Authorization` headers
- [ ] n8n `N8N_BLOCK_ENV_ACCESS_IN_NODE=false` only if required; keys via `$env` not hardcoded
- [ ] Google Sheets OAuth scoped to service account / workspace policy
- [ ] Redis requires auth on `cdp-scrapers-redis-prod`

---

## Data governance checklist

- [ ] Every job has `correlation_id` + `metadata.source`
- [ ] Raw JSON preserved in `muvstok_raw_snapshots` before normalization
- [ ] `muvstok_api_data` row per SKU with `response_status`
- [ ] Errors in `muvstok_errors` with `error_code` / `retryable`
- [ ] Idempotency prevents duplicate jobs from n8n retries
- [ ] Sheet `PROCESSADO` states match job lifecycle (no stuck `processando...` after callback)
- [ ] Results sheet rows traceable via `id_job` = `job_id`

---

## Regression commands

```bash
BASE="https://cdp-muv-api.bravecoast-b14d791e.eastus2.azurecontainerapps.io"
source .env
curl -sS "$BASE/api/v1/muvstok/health"
uv run python scripts/production_audit.py --skus "7703062062,661003M6M00ZZ" --timeout 120
az containerapp logs show -n cdp-muv-worker -g automation --tail 50
# n8n: MCP search_executions workflowId=t160mzGPYYlJcrjZ limit=5
```

---

## Sign-off criteria for 1k SKU production run

1. 5-SKU audit green on API, DB, callback, Sheets, Telegram.
2. `CDP_MUVSTOK_BATCH_SIZE` and worker concurrency tuned (recommend start: batch 5, worker maxReplicas 1).
3. n8n workflows synced to production.
4. DLQ/backlog cleared or understood.
5. Governance rules defined (minimum: not_found vs succeeded, row counts in callback = DB).
6. Rollback: sender stays manual; disable worker scale-up if error rate spikes.
