# CDP Platform — Implementation State

**Last reviewed:** 2026-06-12 · **Live workflow IDs:** [docs/n8n/LIVE_WORKFLOWS.md](../../docs/n8n/LIVE_WORKFLOWS.md)

## Current snapshot

### n8n (production)

Shared n8n model: CDP uses one n8n Container App, `cdp-n8n-prod`, at
`https://automacao.tktechnologies.com.br`. As of the 2026-06-11 cutover,
production Telegram/email/schedule traffic is handled by the `STOKAI - cdp_*`
workflow copies below; the original `cdp_router` and `cdp_progress` workflows
are inactive rollback candidates. Development uses DEV workflow copies inside
the same n8n instance; do not route CDP work through `cdp-n8n-dev` unless a
later approved plan changes this. The existing `cdp-n8n-dev` app is left unused
for CDP and may be decommissioned later with explicit approval.

| Workflow | ID | Webhook / trigger | Last known active version |
|----------|-----|-------------------|---------------------------|
| `cdp_router` | `6id6dkinK9xTLfsb` | Telegram, Gmail, schedule | `d40f065c-7b2e-476e-97e7-f62b3252fea9` (v1 handoff sync, 2026-06-10) |
| `cdp_scraper` | `VfBSV3WU6on8BXm8` | `scraper-result` | `3581b022-e53a-4fe2-a893-7d4d93a33b8c` (v1 handoff sync, 2026-06-10) |
| `cdp_stokapi` | `t160mzGPYYlJcrjZ` | `muvstok-result` | `2c2806f1-3580-4978-af53-5f6e4da8a1f1` (v1 handoff sync, 2026-06-10) |
| `cdp_progress` | `V9I6o32XDoPIRarz` | Schedule | REST activation/update (2026-06-10; MCP not enabled on workflow card) |
| `cdp_notifier` | `ennI9nKin9ruPaLO` | `cdp-notifier` | REST activation/update (Gmail cred `rQesNRyarukVs0N4` + CSV attachment, 2026-06-10; MCP not enabled) |

**Sync:** `make sync-n8n` — inject → patch receivers → build notifier → REST PUT (`scripts/n8n_publish.py`) → MCP `publish_workflow` where available; non-MCP workflows fall back to REST activation. Set `CDP_PROGRESS_WORKFLOW_ID=V9I6o32XDoPIRarz` and `CDP_NOTIFIER_WORKFLOW_ID=ennI9nKin9ruPaLO` (or export before sync) to include progress and notifier.

### n8n (development workflow copies in shared n8n)

| Workflow | ID | Webhook / trigger | Notes |
|----------|----|-------------------|-------|
| `DEV - cdp_router` | `L8foaUWF2CYhp42n` | DEV Telegram (`NoxTKTech_bot` cred `OCT6L7sDZffEbhJ9` in GitHub `development`) | Gmail/schedule disabled; unique webhookIds required on import |
| `DEV - cdp_scraper` | `mjkPMAB0spid7YvU` | `dev-scraper-result` | Uses `CDP_DEV_CALLBACK_WEBHOOK_SECRET` and DEV sheets |
| `DEV - cdp_stokapi` | `Kx7ZQLnaOINhX2Uk` | `dev-muvstok-result` | Uses `CDP_DEV_MUVSTOK_CALLBACK_WEBHOOK_SECRET` and DEV sheets |
| `DEV - cdp_progress` | `DCrWffIqKnpK1wYy` | Schedule | Uses `CDP_DEV_PROGRESS_*` and DEV Telegram credential |
| `DEV - cdp_notifier` | `ssk4HbowArZILiAl` | `dev-cdp-notifier` | Aggregate final Telegram; Gmail disabled on DEV copy |

MCP access is not enabled on the DEV workflow cards as of 2026-06-06, so
MCP `get_workflow_details` / `publish_workflow` cannot inspect or publish the
DEV copies until MCP is enabled in n8n UI/settings for each workflow.

Last DEV sync (2026-06-10): all five DEV copies updated via `make sync-n8n-dev`
(REST PUT + reactivate; same CSV/notifier/router fixes as prod).

### n8n (STOKAI workflow copies in shared n8n)

STOKAI uses workflow copies in the same shared n8n instance. Receivers/notifier
are active, and router/progress were activated for production cutover on
2026-06-11 after explicit approval.

| Workflow | ID | Webhook / trigger | State |
|----------|----|-------------------|-------|
| `STOKAI - cdp_router` | `wjwdSgwc2b017mjG` | Telegram, Gmail, schedule | active |
| `STOKAI - cdp_scraper` | `MZVx4YwXrQVy5aua` | `stokai-scraper-result` | active |
| `STOKAI - cdp_stokapi` | `IV1756ZgTBL6x7lL` | `stokai-muvstok-result` | active |
| `STOKAI - cdp_progress` | `bI2HteRYIvOvGsjN` | Schedule | active |
| `STOKAI - cdp_notifier` | `6CUB7JFG5Jy5D09z` | `stokai-cdp-notifier` | active |

Last STOKAI import/smoke (2026-06-11): `make import-n8n-stokai` imported
router/scraper/stokapi/progress; notifier was imported separately after fixing
`scripts/n8n_import_workflow.py` to omit `description` on `POST /workflows`
(this n8n API rejects that field on create). Callback smoke passed with
executions `3531` (`STOKAI - cdp_scraper`), `3532`
(`STOKAI - cdp_stokapi`), and `3533` (`STOKAI - cdp_notifier`).
Cutover activation (2026-06-11): `cdp_router` (`6id6dkinK9xTLfsb`) and
`cdp_progress` (`V9I6o32XDoPIRarz`) deactivated; `STOKAI - cdp_router` and
`STOKAI - cdp_progress` activated. Trigger check: Telegram credential
`cdp-bot-assistente` (`UmDqGKD8k0bA10j2`), Gmail credential
`gmail lucas@tktech` (`rQesNRyarukVs0N4`), Gmail poll every minute with
`subject:"cdp-enviar-skus"`, and schedule `0 8 * * 1`.

Sheets endpoint rollback (2026-06-12): active STOKAI workflows
`cdp_router`, `cdp_scraper`, `cdp_stokapi`, and `cdp_notifier` were patched
directly via n8n REST + REST reactivation fallback to use the approved workbook
IDs `1IGhsIhrwlnMaCduR-W-eIi9O4mMO2pPYjE-tefgIPII` (SKUs, tab selected by name) and
`1ZBU2d3XVsngOYQH12yU7Mg9DcIzVet2dDmhMtZqHSOo` (Resultados, report link
`gid=2127243308`). Verification rerun was idempotent (`0/4` changed), and
`cdp-n8n-prod` has no `CDP_RESULTADOS_SHEETS_URL` override.

**DEV sync:** `make n8n-dev-workflows` generates local copies under
`n8n/workflows/dev/` (including `dev_cdp_notifier.json`). First import with
`make import-n8n-dev` after creating the DEV Telegram credential in shared
n8n; record the printed IDs in this table. Later updates use
`make sync-n8n-dev` with `CDP_DEV_*_WORKFLOW_ID` exported. Shared n8n DEV env
is configured by `scripts/configure-shared-n8n-dev-env.sh`.

**DEV setup — next steps (human / Azure / n8n UI):**

- [x] DEV Telegram credential configured in GitHub `development`: **NoxTKTech_bot** (`N8N_DEV_TELEGRAM_CREDENTIAL_ID=OCT6L7sDZffEbhJ9`) — 2026-06-12
- [x] `make import-n8n-dev` — workflow IDs recorded above (2026-06-05)
- [x] DEV Google Sheet `1kvkfkqwXgUjW894E3OiNi0rvAh41-uz1ZkfQpxkfnKY` (SKUs + resultados in one workbook; report link gid `2069105059`) — 2026-06-05
- [ ] Confirm DEV Key Vault has `telegram-dev-bot-token`, `api-key`, `callback-webhook-secret`, Muvstok creds for `cdp-muv-api-dev` / worker (current Azure user lacks DEV KV read RBAC)
- [ ] Set GitHub `development` variable `TELEGRAM_DEV_ALLOWED_CHAT_IDS`
- [x] GitHub `development` OIDC secrets configured (`AZURE_*`, `N8N_API_KEY`, `N8N_MCP_AUTH_HEADER`) — 2026-06-12
- [x] Push to `dev` @ `96422e1` — **CD - Development** Azure login unblocked; runtime config still needs DEV chat IDs/KV confirmation
- [ ] Smoke: **dev-cdp-bot** `.sku` → DEV sheets + `dev-scraper-result` / `dev-muvstok-result` / `dev-cdp-notifier`

**n8n Container App:** Production n8n is revision `cdp-n8n-prod--0000026`
with `CDP_ENV=shared`, `WEBHOOK_URL=https://automacao.tktechnologies.com.br/`,
`CDP_SCRAPER_SITES=gm,ml,vw,eu,melibox`, and callback secret env vars backed
by Key Vault secret ref `callback-webhook-secret` (confirmed 2026-06-09).
STOKAI env vars are also configured on the same app:
`CDP_STOKAI_SCRAPER_API_BASE`, `CDP_STOKAI_MUVSTOK_API_BASE`,
`CDP_STOKAI_*_WEBHOOK_PATH`, `CDP_STOKAI_SCRAPER_SITES=gm,ml,vw,eu,melibox`,
and STOKAI API/callback secrets via Container App secret refs
`cdp-stokai-*` (confirmed 2026-06-11).

2026-06-12 repo sync: `make sync-n8n-dev` and `make sync-n8n-stokai`
published all five DEV workflow copies and all five STOKAI workflow copies
through n8n REST with REST reactivation fallback. Read-back confirmed DEV and
STOKAI workflow copies active with expected node counts; original rollback
`cdp_router` and `cdp_progress` stayed inactive.

**Email command whitelist:** Production n8n has `EMAIL_ALLOWED_SENDERS=dev.lucascruz@gmail.com,peron@sopecasgenuinas.com.br` (confirmed 2026-06-09; inherited by current Container App revision unless intentionally changed). Keep the user whitelist on; add future users as comma-separated emails.

**Email command trigger:** Gmail Trigger filters `subject:"cdp-enviar-skus"`. Put `.analisar` or `.sku ...` at the start of the subject or first body line.

**STOKAI email recovery (2026-06-12):** Gmail `.analisar` execution `3856`
started Scraper job `2b5bc112-faa1-4fff-a862-656d4deb495b` for batch
`bg-mqb7jdkx-92hyo0`, but API Diversos dispatch failed with `401 Invalid API
key`; execution `3853` just before it read 0 CDP_SKUs rows. Root cause was
`cdp-stokai-muv-api` retaining a stale 32-character `api-keys` Container App
secret while `cdp-stokai-kv-prod/api-key` and n8n STOKAI secrets were 64
characters. Refreshed `api-keys` from Key Vault, stripped CR, restarted
revision `cdp-stokai-muv-api--0000001`, and verified auth accepted via a
nonexistent-job probe returning `404`. Resumed the missing API Diversos arm as
job `d1db1a02-cb0b-4151-a939-c37143f46598`; receiver execution `3876` and
notifier execution `3877` succeeded and sent the final email. The dispatch run
`e1af86d6-8780-4a64-965c-1f602decace5` is patched to
`final_notification_status=sent`, `final_channel=email`. Published a
`STOKAI - cdp_notifier` fix (REST update + REST reactivation fallback; MCP
still disabled) so `PATCH final-notification` uses
`CDP_STOKAI_SCRAPER_API_BASE` / `CDP_STOKAI_API_KEY`. Also published a
`STOKAI - cdp_router` fix for execution `3853`, where `📊 Ler CDP_SKUs`
returned 0 rows and the workflow ended silently: the sheet read now always
emits an empty item, DQ counts it as 0 rows, `.analisar` replies with
`Consulta CDP sem peças pendentes`, and API Diversos error formatting unwraps
object-shaped errors instead of `[object Object]`. Live read-back confirmed the
router is active with those fixes.

**GitHub:** `tktech/main` and `tktech/dev` @ `96422e1` (v1 handoff, 2026-06-10); CI green on Scraper + Contracts; StokAPI lint fixed in follow-up commit. GitHub OIDC app registrations created 2026-06-12: DEV client `05123bc9-e960-4fd6-8fb7-2e2471f91c4a` (`environment:development`, scoped to `automation` + ACR + DEV KV); PROD client `cf0b1694-d3fb-486e-b780-a98425e159ae` (`environment:production`, scoped to `automation`, `stokai-tk`, both ACRs, and prod/STOKAI KVs). GitHub `production` environment now has OIDC, n8n, and STOKAI CD secrets/vars; no required-review protection is configured yet.

### Scraper (`scrapers/`)

| Item | Value |
|------|--------|
| Stack | FastAPI, Celery, Playwright, PostgreSQL, Redis DB 0/1 |
| Azure prod | `cdp-scrapers-api-prod`, `cdp-scrapers-worker-prod` |
| Last deploy | 2026-06-10 — `cdpscraperprodacr.azurecr.io/cdp-scraper:20260610-1443` (v1 handoff GitHub sync) |
| Azure dev | `cdp-scrapers-api-dev`, `cdp-scrapers-worker-dev` — image `dev-20260602-2106`; API `https://cdp-scrapers-api-dev.happyforest-06c871e6.eastus2.azurecontainerapps.io`; secrets in `cdp-scrapers-kv-dev` |
| Cache | 24h TTL; router `force_refresh: false` |
| Sites | gm, ml, vw, eu, melibox (`CDP_SCRAPER_SITES`); pecadireta/goparts/procurapecas/ebay disabled pending smoke |
| Proxy | IPRoyal ISP BR (2 IPs) — **prod Melibox OK 2026-06-09** (egress `172.193.112.98` whitelisted); KV persist pending RBAC |

### StokAPI (`muvstok-api/`)

| Item | Value |
|------|--------|
| Stack | FastAPI, Redis Streams worker, PostgreSQL |
| Azure prod | `cdp-muv-api`, `cdp-muv-worker` |
| Last deploy | 2026-06-10 — `cdpscraperprodacr.azurecr.io/cdp-muv-api:20260610-1448`, `cdpscraperprodacr.azurecr.io/cdp-muv-worker:20260610-1448` (v1 handoff GitHub sync) |
| Azure dev | `cdp-muv-api-dev`, `cdp-muv-worker-dev` not present as of 2026-06-06 audit; scripts ready, but deployment requires DEV Key Vault access/secrets |

### STOKAI production (`stokai-tk`)

STOKAI is a separate CDP production resource group. `automation` remains the
backup/rollback environment; n8n is not deployed in `stokai-tk`.

| Item | Value |
|------|-------|
| Resource group | `stokai-tk` |
| ACR | `cdpstokaitkacr` |
| Key Vault | `cdp-stokai-kv-prod` |
| Postgres | `cdp-stokai-pg-prod` / DB `cdp_scraper` |
| Redis | `cdp-stokai-redis-prod` |
| Container Apps env | `cdp-stokai-prod-env` |
| Pull identity | `cdp-stokai-prod-pull` |
| Scraper API | `cdp-stokai-scrapers-api-prod` → `https://cdp-stokai-scrapers-api-prod.bluewater-4bfb07b7.eastus2.azurecontainerapps.io` |
| Scraper worker | `cdp-stokai-scrapers-worker-prod` |
| StokAPI API | `cdp-stokai-muv-api` → `https://cdp-stokai-muv-api.bluewater-4bfb07b7.eastus2.azurecontainerapps.io` |
| StokAPI worker | `cdp-stokai-muv-worker` (no ingress; background Redis worker) |
| Images | scraper `cdpstokaitkacr.azurecr.io/cdp-scraper:20260610-2244`; StokAPI API `cdpstokaitkacr.azurecr.io/cdp-muv-api:20260612-1406`; StokAPI worker `cdpstokaitkacr.azurecr.io/cdp-muv-worker:20260612-1406` |
| Validation | 2026-06-11: all four active revisions `Healthy`; health OK; Redis `Succeeded`; Postgres `Ready`; migrations at scraper `3c9a6b4e0d12` and StokAPI `20260608_0005`. IPRoyal/Melibox fixed and verified: `proxy-urls` populated in `cdp-stokai-kv-prod`, scraper API/worker revision `0000002` with `PROXY_ROTATION_ENABLED=true`, outbound IP `135.222.160.56`, Melibox lookup `51766536` returned `FOUND_PRICE` with 16 priced exact rows, best BRL 547.20. Scraper worker job `3de1919c-8d16-4bae-aff3-a3fa61317aba` completed with `FOUND_PRICE`; DB has 16 `part_results` priced exact rows. StokAPI job `91b8405a-83e2-4367-96d8-3194706e40a0` succeeded; DB has one `muvstok_api_data` row with `response_status=FOUND_PRICE`. STOKAI n8n callback smoke passed: scraper job `8cd465d5-3ae7-4c8a-9701-e38e0d7366c7`, StokAPI job `382e78df-84ee-4337-a5b1-39e5beaa49bf`, executions `3531`/`3532`/`3533` all `success`. Fresh GM smoke for prior SKU `22781768` returned `NOT_FOUND`, so use Melibox `51766536` as the current price-positive scraper gate. 2026-06-12 real email `.sku` batch `bg-mqa5vfos-4frs5b` completed: scraper job `40bd188f-1069-417b-9098-b30ddac7b346` processed 2/2 SKUs as `FOUND_PRICE`; StokAPI job `9933317c-85f9-4d80-8e89-ec2ce8b67637` succeeded; n8n pipeline-result callbacks reached the dispatch-run API at `00:02:30Z` and `00:05:59Z`. |
| Next gate | Enable MCP visibility for STOKAI workflow copies if execution-history inspection is needed through MCP |

Deployment fixes from validation:

- `cdp-stokai-muv-api` had a stale 32-character Container App secret
  `api-keys` while Key Vault `api-key` was 64 characters; refreshed the
  Container App secret from Key Vault and restarted the API revision.
- `cdp-stokai-muv-worker` was marked `Degraded` because it had internal HTTP
  ingress despite being a background worker; disabled ingress for the live app
  and set `WORKER_INGRESS_ENABLED=false` in the STOKAI wrapper.
- `cdp-stokai-scrapers-*` had `PROXY_ROTATION_ENABLED=true` with empty
  `proxy-urls`; live STOKAI scraper API/worker were set to
  `PROXY_ROTATION_ENABLED=false`, and deploy scripts now auto-disable rotation
  when no usable proxy URL is configured.
- 2026-06-11 follow-up: STOKAI `proxy-urls`/Melibox secrets were applied from
  the local IPRoyal config into `cdp-stokai-kv-prod` and the STOKAI scraper
  API/worker; active revisions now have `PROXY_ROTATION_ENABLED=true` and
  Melibox price smokes pass.
- `cdp-stokai-muv-worker` emitted repeated Azure scaler errors for missing
  HTTP metrics (`s0-upstream_rq_total`) even though it is a fixed Redis
  consumer; live worker was pinned to min/max `1`, and the worker deploy script
  now defaults to no ingress and one replica.
- 2026-06-12 cache hardening: STOKAI scraper API/worker active revisions
  `0000003` set `SCRAPE_CACHE_TTL_NOT_FOUND_SECONDS=86400` and
  `SCRAPE_CACHE_TTL_BLOCKED_SECONDS=86400` to avoid same-day repeat Playwright
  requests for the same SKU/site. Redis DB 1 was rehydrated for email batch
  `bg-mqa5vfos-4frs5b` with 10 per-site keys at 24h TTL; repeat lookup for
  `5U6959775` returned `cache_hits=5`, `live_scrapes=0`, all `from_cache=true`.

### Email aggregate delivery (live 2026-06-10)

- **Incident fix:** `cdp_notifier` `📧 Email: resultado final` used placeholder Gmail cred `gmail` (missing in n8n) → exec `2985` failed; router uses `rQesNRyarukVs0N4` (`gmail lucas@tktech`). Patched in `build_cdp_notifier_workflow.py` + `patch_cdp_notifier_workflow.py`; replay exec `2988` sent batch `bg-mq89wbul-r27og0` / job `1ebc3ebc-0c10-43e9-aaa5-33230ca313d3`.
- Live: aggregate final email includes job-scoped CSV; `GET /api/v1/dispatch-runs/by-batch/{id}`; claim includes job IDs; StokAPI dispatch errors email requester; Melibox `blocked` alone → ops **Warning** not Error.

### Shared

- Router/progress Code: `n8n/src/` → inject via `scripts/sync_workflow_code_from_shared.py`
- Contracts: `contracts/*.schema.json`
- Environments: [ADR-0006](../../docs/decisions/ADR-0006-dev-production-environments.md)
- Reporting contract (2026-06-03): Scraper and API Diversos callbacks carry
  `sku_result`/`status_resultado`, `source_health`, and `has_valid_price`.
  Sheets/Telegram/Painel count found only as `FOUND_PRICE` with
  `has_valid_price=true`; `NO_PRICE`, `NOT_FOUND`, `BLOCKED`, `TIMEOUT`,
  `ERROR`, and `NOT_QUERIED` stay separate. Mercado Livre/protected-source
  blocks are `BLOCKED`, not `NOT_FOUND`.
- Seller reporting contract (2026-06-03): `Detalhado` uses `vendedor`, `uf`,
  `empresa`, `cnpj`; scraper payload/DB field is `seller_uf`; API Diversos
  receiver accepts raw `estado` aliases but writes only `uf`.
- Production Scraper DB schema (2026-06-08): Alembic migrations
  `2b7f0d6c1a94` and `3c9a6b4e0d12` are applied in prod. They add aggregate
  `dispatch_runs` final-notification fields and `part_results` seller metadata
  columns (`seller_uf`, `seller_company_name`, `seller_cnpj`).
- Notifier Telegram credential fix (2026-06-09): live `cdp_notifier` used placeholder
  credential id `telegram` (missing in n8n); repo + live now use `cdp-bot-assistente`
  (`UmDqGKD8k0bA10j2`). Replay for batch `bg-mq6q5741-gy2xzm` delivered via exec `2389`.
  `dispatch_runs` allows reclaim after `final_notification_status=failed` (deployed `20260609-1355`).
- SKUs robot columns fix (2026-06-09 follow-up): executions `2612`, `2613`,
  and `2615` read/remapped CDP_SKUs rows correctly but Google Sheets update
  nodes returned 0 items because update schemas targeted base keys
  `PROCESSADO`/`ENCONTRADO`/`NOTIFICADO` while the tab headers are
  `PROCESSADO 🤖`/`ENCONTRADO 🤖`/`NOTIFICADO 🤖`. Router, scraper receiver,
  StokAPI receiver, and notifier now patch exact robot-header keys and preserve
  Google Sheets row lineage. Published router `e0303e69`, scraper `39f2706f`,
  StokAPI `e24e2a30`, progress/notifier REST update-reactivate.
- Blocked-site audit (2026-06-09): latest inspected run
  `fb6be457-373b-41a5-8087-621e782d05e8` / batch `bg-mq73py7r-h2aw1f`
  replayed cached scraper results (`force_refresh=false`, all site results
  `from_cache=true`). `goparts`, `procurapecas`, and `ebay` were archived
  placeholders; `pecadireta` had cached HTTP 403 anti-bot blocks. Live n8n
  `CDP_SCRAPER_SITES` now disables those four sites and keeps
  `gm,ml,vw,eu,melibox`.
- Telegram UX (2026-06-09): removed end-user warning about blocked/timeout sources from
  final notifier message; `appendAttribution: false` enforced on notifier Telegram node.
- Redis cache (2026-06-09): batch `bg-mq6q5741-gy2xzm` scraper job used `from_cache: true`
  for all site results (`force_refresh: false`); cache working as designed.
- Redis cache (2026-06-12): scraper cache policy now keeps `success`,
  `no_price`, `not_found`, and `blocked` site results for 24h; `error` and
  `timeout` remain uncached.
- Results sheet (2026-06-09): exec `2371` Detalhado/Histórico/Resumo saves succeeded for
  batch `bg-mq6q5741-gy2xzm`; intake SKUs tab D–F was the separate lineage bug above.
- Callback handoff smoke (2026-06-09): batch
  `bg-codex-positive-20260609134721` completed Scraper `06bf5beb-9bc3-41dd-85b0-d5de3f10c2bb`
  and StokAPI `bbb439e9-7b4e-40b2-be4e-99b91eaeadea`; n8n executions
  `2356` (`cdp_scraper`), `2355` (`cdp_stokapi`), and `2358`
  (`cdp_notifier`) succeeded. `pipeline-result` returned
  `both_terminal=true`, `ready_for_final=true`, and final notification patch
  succeeded with no delivery target for the controlled smoke.
- Telegram final delivery evidence (2026-06-08): `cdp_notifier` execution
  `2067` for batch `bg-mq5kmekg-2iiivj` ran `📱 Telegram: resultado final`
  and patched `final_channel=telegram` with no final error.

## Known gaps

| Gap | Mitigation |
|-----|------------|
| BR ISP proxy KV persist | STOKAI KV/app proxy config is persisted and smoke-tested as of 2026-06-11; confirm whether the older `automation` prod KV persistence gap is still relevant before changing rollback prod |
| `N8N_API_KEY` in `~/.cursor/mcp.json` | Use `muvstok-api/.env` or export `N8N_API_KEY` before `make sync-n8n` |
| StokAPI dev Container Apps | `muvstok-api/scripts/deploy_muv_dev.sh` now creates/updates `cdp-muv-api-dev` and `cdp-muv-worker-dev`; requires dev KV DB/Redis/API/callback secrets and Muvstok credentials |
| Legacy `scrapers/n8n/` removed | Platform n8n docs at `docs/n8n/` |
| n8n MCP disabled on `cdp_progress`, `cdp_notifier`, and DEV copies | Enable MCP access from each n8n workflow card/settings, then rerun MCP inspection/publish |
| DEV Key Vault RBAC unavailable for current Azure identity | GitHub DEV OIDC SP has `Key Vault Secrets User`; current interactive Azure user still lacks DEV KV read RBAC, so confirm DEV secrets through CI or grant temporary read access |

## Changelog (abbreviated)

<details>
<summary>2026-05-27 — 2026-06-09 ops history</summary>

- **2026-06-09:** Callback webhook audit/fix — production n8n `CDP_ENV`
  set to `shared`, workflow DEV detection now uses workflow names only,
  Scraper/StokAPI receiver secret checks trim and fail closed, `cdp_notifier`
  webhook reactivated, and positive aggregate smoke verified automatic
  receiver → notifier handoff. DEV workflow copies were also synced and
  smoke-checked.
- **2026-06-08:** Incident recovery for Telegram `.analisar` batch
  `bg-mq55sfji-t8qgdz` — applied missing Scraper DB migrations, replayed the
  replacement scraper job, fixed `cdp_notifier` `ready_for_final=true` branch
  wiring, retried notifier handoff, and verified final notification patch.
- **2026-06-05:** Targeted n8n template publish — confirmation/result copy clarifies WEBSCRAPERS + ESTOQUE ONLINE result messages; router `a9a34416-d362-46a1-9d05-bc8583df42b3`, scraper `4a4ecf8c-0ce8-4aea-a864-7b510a91c7ea`, StokAPI `eb5ae450-ad4e-4f44-8d30-022067f31b3a`.
- **2026-06-05:** Full n8n sync (`make sync-n8n`) — router `bb52096d-aff9-4895-941b-0391643a75d7`, scraper `67be3cf3-fb6b-425a-a55a-340cb713b5f9`, StokAPI `c6eca24d-eefa-4932-90e2-9292614d8667`, progress REST activation (10 nodes).
- **2026-06-03:** Full n8n sync — router `386c1189-ed2c-4066-bb3b-6261639b5c2f`, scraper receiver `a276757b-75e4-4c72-a363-c680b306f08f`, StokAPI receiver `83609477-6be4-4f5e-9f0f-b3fbe9e4296d`, progress `2055041e-24bf-4cd2-a741-9289ef30acdc`.
- **2026-06-03:** Router email confirmation fix `10180203-2562-4764-bd75-56e9fabe7f41` — email `.sku` confirmations no longer copy the email address into `chat_id` or route to Telegram.
- **2026-06-03:** Router Gmail subject patch `e828a392-b184-46f9-95d9-5a63dd5a455f` — Gmail Trigger now filters `subject:"cdp-enviar-skus"`.
- **2026-06-03:** Enabled production email command whitelist via `EMAIL_ALLOWED_SENDERS=dev.lucascruz@gmail.com` on `cdp-n8n-prod--0000019`, then appended `peron@sopecasgenuinas.com.br` on `cdp-n8n-prod--0000020`; future users should be appended to the whitelist, not disable it.
- **2026-06-03:** Router hotfix `75b59078-6d6e-452b-bd45-4f78be63e535` — removed Code-node HTTP dispatch after live `fetch_unavailable`; dispatch uses HTTP Request nodes again.
- **2026-06-03:** Router dispatch fixed to use n8n HTTP Request nodes for Scraper + API Diversos; Code nodes only prepare payloads. Scraper POST sends `force_refresh: false`, dispatch HTTP nodes continue on failure, and `dispatch-runs` registration merges branch job IDs.
- **2026-06-03:** Reporting contract hardened in live receiver workflows and
  local contracts — `FOUND_PRICE`, `NO_PRICE`, `NOT_FOUND`, `BLOCKED`,
  `TIMEOUT`, `ERROR`, and `NOT_QUERIED` stay distinct.
- **2026-06-02:** Full platform sync — GitHub push, n8n publish (router/scraper/stokapi/progress), scraper image `20260602-2102`, dev stack deploy script + ADR-0006, `n8n_publish.py` settings sanitizer.
- **2026-06-01:** Agent workspace audit; `scripts/n8n_publish.py` REST + MCP publish.
- **2026-05-30:** Router StokAPI-before-scraper; scraper Telegram evidence-based messages.
- **2026-05-29:** Dup-SKU end-to-end (StokAPI cache + N results).

</details>
