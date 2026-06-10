# CDP Platform — Implementation State

**Last reviewed:** 2026-06-10 · **Live workflow IDs:** [docs/n8n/LIVE_WORKFLOWS.md](../../docs/n8n/LIVE_WORKFLOWS.md)

## Current snapshot

### n8n (production)

Shared n8n model: CDP uses one n8n Container App, `cdp-n8n-prod`, at
`https://automacao.tktechnologies.com.br`. Production workflows keep the IDs
below. Development uses DEV workflow copies inside the same n8n instance; do
not route CDP work through `cdp-n8n-dev` unless a later approved plan changes
this. The existing `cdp-n8n-dev` app is left unused for CDP and may be
decommissioned later with explicit approval.

| Workflow | ID | Webhook / trigger | Last known active version |
|----------|-----|-------------------|---------------------------|
| `cdp_router` | `6id6dkinK9xTLfsb` | Telegram, Gmail, schedule | `08832e1d-30c0-4e7f-b52b-0fcc671e1481` (StokAPI dispatch email errors, 2026-06-10) |
| `cdp_scraper` | `VfBSV3WU6on8BXm8` | `scraper-result` | `62231bd4-fec4-41aa-b276-6debeefe6983` (Melibox blocked → ops warning, 2026-06-10) |
| `cdp_stokapi` | `t160mzGPYYlJcrjZ` | `muvstok-result` | `a67c819f-8498-4d59-88c9-f4e2da3b6571` (2026-06-10) |
| `cdp_progress` | `V9I6o32XDoPIRarz` | Schedule | REST activation/update (2026-06-10; MCP not enabled on workflow card) |
| `cdp_notifier` | `ennI9nKin9ruPaLO` | `cdp-notifier` | REST activation/update (Gmail cred `rQesNRyarukVs0N4` + CSV attachment, 2026-06-10; MCP not enabled) |

**Sync:** `make sync-n8n` — inject → patch receivers → build notifier → REST PUT (`scripts/n8n_publish.py`) → MCP `publish_workflow` where available; non-MCP workflows fall back to REST activation. Set `CDP_PROGRESS_WORKFLOW_ID=V9I6o32XDoPIRarz` and `CDP_NOTIFIER_WORKFLOW_ID=ennI9nKin9ruPaLO` (or export before sync) to include progress and notifier.

### n8n (development workflow copies in shared n8n)

| Workflow | ID | Webhook / trigger | Notes |
|----------|----|-------------------|-------|
| `DEV - cdp_router` | `L8foaUWF2CYhp42n` | DEV Telegram (`dev-cdp-bot` cred `wblrlkXu6SW1M5M1`) | Gmail/schedule disabled; unique webhookIds required on import |
| `DEV - cdp_scraper` | `mjkPMAB0spid7YvU` | `dev-scraper-result` | Uses `CDP_DEV_CALLBACK_WEBHOOK_SECRET` and DEV sheets |
| `DEV - cdp_stokapi` | `Kx7ZQLnaOINhX2Uk` | `dev-muvstok-result` | Uses `CDP_DEV_MUVSTOK_CALLBACK_WEBHOOK_SECRET` and DEV sheets |
| `DEV - cdp_progress` | `DCrWffIqKnpK1wYy` | Schedule | Uses `CDP_DEV_PROGRESS_*` and DEV Telegram credential |
| `DEV - cdp_notifier` | `ssk4HbowArZILiAl` | `dev-cdp-notifier` | Aggregate final Telegram; Gmail disabled on DEV copy |

MCP access is not enabled on the DEV workflow cards as of 2026-06-06, so
MCP `get_workflow_details` / `publish_workflow` cannot inspect or publish the
DEV copies until MCP is enabled in n8n UI/settings for each workflow.

Last DEV sync (2026-06-10): all five DEV copies updated via `make sync-n8n-dev`
(REST PUT + reactivate; same CSV/notifier/router fixes as prod).

**DEV sync:** `make n8n-dev-workflows` generates local copies under
`n8n/workflows/dev/` (including `dev_cdp_notifier.json`). First import with
`make import-n8n-dev` after creating the DEV Telegram credential in shared
n8n; record the printed IDs in this table. Later updates use
`make sync-n8n-dev` with `CDP_DEV_*_WORKFLOW_ID` exported. Shared n8n DEV env
is configured by `scripts/configure-shared-n8n-dev-env.sh`.

**DEV setup — next steps (human / Azure / n8n UI):**

- [x] DEV Telegram credential: **dev-cdp-bot** (`N8N_DEV_TELEGRAM_CREDENTIAL_ID=wblrlkXu6SW1M5M1`) — 2026-06-06
- [x] `make import-n8n-dev` — workflow IDs recorded above (2026-06-05)
- [x] DEV Google Sheet `1kvkfkqwXgUjW894E3OiNi0rvAh41-uz1ZkfQpxkfnKY` (SKUs + resultados in one workbook; report link gid `2069105059`) — 2026-06-05
- [ ] Confirm DEV Key Vault has `api-key`, `callback-webhook-secret`, Muvstok creds for `cdp-muv-api-dev` / worker
- [ ] Set GitHub `development` secrets/vars per [docs/ENVIRONMENTS.md](../../docs/ENVIRONMENTS.md)
- [ ] Push to `dev` → **CD - Development** (images + `configure-shared-n8n-dev-env.sh` + `sync-n8n-dev`)
- [ ] Smoke: **dev-cdp-bot** `.sku` → DEV sheets + `dev-scraper-result` / `dev-muvstok-result` / `dev-cdp-notifier`

**n8n Container App:** Production n8n is revision `cdp-n8n-prod--0000025`
with `CDP_ENV=shared`, `WEBHOOK_URL=https://automacao.tktechnologies.com.br/`,
`CDP_SCRAPER_SITES=gm,ml,vw,eu,melibox`, and callback secret env vars backed
by Key Vault secret ref `callback-webhook-secret` (confirmed 2026-06-09).

**Email command whitelist:** Production n8n has `EMAIL_ALLOWED_SENDERS=dev.lucascruz@gmail.com,peron@sopecasgenuinas.com.br` (confirmed 2026-06-09; inherited by current Container App revision unless intentionally changed). Keep the user whitelist on; add future users as comma-separated emails.

**Email command trigger:** Gmail Trigger filters `subject:"cdp-enviar-skus"`. Put `.analisar` or `.sku ...` at the start of the subject or first body line.

**GitHub:** `tktech/main` and `tktech/dev` @ `3daf582`; `origin/main` was 6 commits behind before the 2026-06-06 sync pass.

### Scraper (`scrapers/`)

| Item | Value |
|------|--------|
| Stack | FastAPI, Celery, Playwright, PostgreSQL, Redis DB 0/1 |
| Azure prod | `cdp-scrapers-api-prod`, `cdp-scrapers-worker-prod` |
| Last deploy | 2026-06-10 — `cdpscraperprodacr.azurecr.io/cdp-scraper:20260610-1309` (`GET /dispatch-runs/by-batch`, extended claim fields) |
| Azure dev | `cdp-scrapers-api-dev`, `cdp-scrapers-worker-dev` — image `dev-20260602-2106`; API `https://cdp-scrapers-api-dev.happyforest-06c871e6.eastus2.azurecontainerapps.io`; secrets in `cdp-scrapers-kv-dev` |
| Cache | 24h TTL; router `force_refresh: false` |
| Sites | gm, ml, vw, eu, melibox (`CDP_SCRAPER_SITES`); pecadireta/goparts/procurapecas/ebay disabled pending smoke |
| Proxy | IPRoyal ISP BR (2 IPs) — **prod Melibox OK 2026-06-09** (egress `172.193.112.98` whitelisted); KV persist pending RBAC |

### StokAPI (`muvstok-api/`)

| Item | Value |
|------|--------|
| Stack | FastAPI, Redis Streams worker, PostgreSQL |
| Azure prod | `cdp-muv-api`, `cdp-muv-worker` |
| Last deploy | 2026-06-08 — `cdpscraperprodacr.azurecr.io/cdp-muv-api:20260608-1545`, `cdpscraperprodacr.azurecr.io/cdp-muv-worker:20260608-1545` (`cdp-muv-api--0000012`, `cdp-muv-worker--0000013`) |
| Azure dev | `cdp-muv-api-dev`, `cdp-muv-worker-dev` not present as of 2026-06-06 audit; scripts ready, but deployment requires DEV Key Vault access/secrets |

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
| BR ISP proxy KV persist | KV `proxy-urls` / melibox creds still need Secrets Officer for deploy durability |
| `N8N_API_KEY` in `~/.cursor/mcp.json` | Use `muvstok-api/.env` or export `N8N_API_KEY` before `make sync-n8n` |
| StokAPI dev Container Apps | `muvstok-api/scripts/deploy_muv_dev.sh` now creates/updates `cdp-muv-api-dev` and `cdp-muv-worker-dev`; requires dev KV DB/Redis/API/callback secrets and Muvstok credentials |
| Legacy `scrapers/n8n/` removed | Platform n8n docs at `docs/n8n/` |
| n8n MCP disabled on `cdp_progress`, `cdp_notifier`, and DEV copies | Enable MCP access from each n8n workflow card/settings, then rerun MCP inspection/publish |
| DEV Key Vault RBAC unavailable for current Azure identity | Grant secret metadata/value access or run DEV CD with configured GitHub environment secrets |

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
