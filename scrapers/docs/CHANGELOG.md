# Changelog

> Agent workspace moved from `.claude/` to `.agent/` (2026-05-27). Historical entries below may still mention `.claude/` paths.

## 2026-06-02
- IPRoyal setup runbook: `docs/runbooks/iproyal-isp-proxy-setup.md` (purchase → local → Azure).
- Proxy rollout workflow: `.agent/workflows/proxy-rollout.md`, `scripts/proxy_site_smoke.py`.
- ML production curl smoke SKU `51766536` (replaces stale `06K907811B`).
- Ops docs aligned: `MAINTENANCE_CHECKPOINT.md`, service/platform `implementation-state.md`, `AGENTS.md` proxy section.
- `.env.production.example`: removed duplicate Melibox credentials; documented fail-closed proxy requirement.

## 2026-05-22
- Parallel live scrapes: default `SCRAPE_SITES_SEQUENTIAL=false` with
  `max_concurrent_scrapers=3` (3 sites per SKU wave). Updated cold-run duration
  estimates in API (`job_estimate.py`) and n8n Telegram confirmations (~4 min for
  5 SKUs × 5 sites instead of ~2 min).
- Reduced multi-SKU job latency: skip repeated live session probes within
  `SESSION_RECHECK_SECONDS` (default 15m) per worker; EU Imports uses
  `domcontentloaded` instead of `networkidle`; job duration estimate reflects
  sequential cold scrapes (~12s/site).
- Fixed Celery worker log levels: replaced `structlog.PrintLoggerFactory` with
  stdlib logging so INFO events no longer appear as `WARNING/ForkPoolWorker-*`
  (stdout capture). Worker children call `setup_logging()` via
  `worker_process_init`.

## 2026-05-21
- Published A28 live n8n workflows from repo exports (`cdp_analise`, `cdp_resultado`) via MCP SDK;
  aligned dispatcher `/jobs` contract and receiver webhook secret env check.
- Added `scripts/n8n_workflow_json_to_sdk.mjs` for MCP publish pipeline.
- Deployed A27 callback fix to production (`callback-strip-20260521-1649` on API +
  worker): automated worker → n8n callbacks PASS (E2E job `86f8b3a4-...`, n8n
  execution 369). Fixed `test_5sku_n8n_e2e.sh` JSON body corruption (stderr for SKU list).
- Added maintenance handoff `docs/MAINTENANCE_CHECKPOINT.md` and n8n audit
  `n8n/docs/AUDIT_2026-05-21.md` (live vs repo drift, callback blocker).
- Production validation: 5/5 SKU scrape cache on `/lookup` and `/jobs`; 5-SKU E2E
  batch job completed in Azure; worker callback failed (`\r` in webhook secret);
  n8n receiver OK when payload delivered with trimmed secret (execution 361).
- Added `scripts/production_sku_pool.py` and wired random 5-SKU sampling into
  `test_production_5sku_cache_audit.py`, `test_production_5sku_jobs_cache_audit.py`,
  and `test_5sku_n8n_e2e.sh` (`--seed` / `PRODUCTION_TEST_SKU_SEED`).
- Fixed `src/config.py` to strip `\r\n` from `api_key` and
  `callback_webhook_secret` (pending production deploy).
- Fixed `POST /lookup` to run cache-aware scrapes in the API process instead of
  enqueueing Celery (removed ~10s queue overhead on cache hits). Production image:
  `lookup-direct-20260521-1439`.
- Added `scripts/test_production_5sku_cache_audit.py` — 5-SKU live + cached curl
  audit for production (`docs/validation/latest_production_5sku_cache_audit.json`).
- Deployed scrape cache to Azure production (`cdp-scrapers-api-prod`,
  `cdp-scrapers-worker-prod`, image `scrape-cache-ssl-20260521-1402`):
  `SCRAPE_CACHE_REDIS_URL` on Redis DB 1 with `ssl_cert_reqs=CERT_NONE`,
  production smoke PASS (`from_cache=true`, `cache_hits=1`, `live_scrapes=0`).
- Fixed Azure Redis TLS for scrape cache (`scrape_cache.py` + Bicep URL) and
  persisted `from_cache` / `cache_hits` / `live_scrapes` through job DB reads.
- Hardened production smoke scripts to strip CR/LF from Key Vault / `az` output.
- Added scrape cache smoke scripts (`scripts/test_scrape_cache_local.sh`,
  `scripts/test_scrape_cache_production.sh`), operations runbook
  `docs/SCRAPE_CACHE_OPERATIONS.md`, and agent prompt
  `.claude/prompts/scrape-cache-local-and-azure.md` for local → Azure validation.
- Wired Azure Container Apps env vars for `SCRAPE_CACHE_*` in
  `infra/modules/container-app.bicep` and `infra/main.bicep` (Redis DB 1).
- Added Redis-backed scrape result cache (`src/services/scrape_cache.py`):
  per-site SKU snapshots with 24h default TTL, shorter TTL for `not_found` and
  `blocked`, PostgreSQL warm fallback, and graceful degradation when Redis is
  down.
- Wired cache into orchestrator and `/api/v1/lookup` / `/jobs` via
  `force_refresh`, `SiteResult.from_cache`, and `SKUResult.cache_hits` /
  `live_scrapes`. Live scrapes for cache misses run sequentially by default
  (`SCRAPE_SITES_SEQUENTIAL=true`) to reduce anti-bot risk.
- Documented behavior in `docs/SPECS/SCRAPE_CACHE_SPEC.md` and `.env.example`.

## 2026-05-19
- Re-ran the all-source interview demo with the supplied SKU map after the
  anti-bot fixes. Current live result from this network: 7/9 sources return
  prices (GM, Mercado Livre, VW, EU Imports, Peça Direta, eBay, Melibox);
  GoParts and Procura Peças return Cloudflare managed challenges (`blocked`).
- Fixed two demo price misses: Mercado Livre now opens ambiguous search
  candidates and verifies the part number on the product detail page, while
  eBay ignores hidden challenge markup when real search results are visible.
  GoParts now detects headless Cloudflare challenge responses before browser
  navigation so the demo reports `blocked` quickly instead of timing out.
- Updated local demo/test SKU coverage to the supplied all-source map:
  GM `93240598`, VW `5X9827550A`, Procura Peças `51766536`, Mercado Livre
  `51766536`, EU Imports `03L115562`, eBay `5473368`, GoParts `7091011`, Peça
  Direta `7091011`, and Melibox `51766536`. Demo runners can instantiate
  archived scrapers for manual all-source checks without adding them back to
  production defaults.
- Fixed a scraper demo regression from the anti-bot update: removed the
  context-wide `Upgrade-Insecure-Requests` header so browser-only navigation
  headers are no longer forced onto every XHR/API request, slowed the interview
  demo's default browser pace, and made GM wait for dealer-price rows before
  extracting product details.
- Added shared anti-bot hardening to `BaseScraper`: realistic Chromium context
  profile with locale/timezone/viewport/headers, optional JSON user-agent
  rotation, low-risk webdriver signal cleanup, main-document `403` / `429`
  detection, bounded anti-bot backoff, and explicit `blocked` results when
  access remains restricted.
- Added anti-bot environment knobs to `.env.example` and
  `.env.production.example`, plus focused tests for browser profile construction
  and HTTP block-response detection.
- Added a local-only N8N workflow export,
  `n8n/workflows/local_interview_demo.json`, plus matching settings metadata.
  It can trigger the local FastAPI `/api/v1/demo/interview` endpoint, poll the
  demo status URL, and format the same summary produced by `make
  interview-demo`.
- Documented the local N8N interview demo workflow, including host vs Docker
  API base URL guidance and the local demo API endpoints.

## 2026-05-14
- Aligned `.claude/` agent guidance with the current CDP scraper architecture:
  rewrote the copied-project `start-new-chat` prompt, added the missing
  `start-maintenance-chat` command, expanded AI-assisted skill routing, fixed
  stale n8n/documentation rules, and updated `.claude/settings.json`.
- Configured the live N8N Container App custom-domain runtime values:
  `N8N_HOST=automacao.tktechnologies.com.br`,
  `N8N_EDITOR_BASE_URL=https://automacao.tktechnologies.com.br`, and
  `WEBHOOK_URL=https://automacao.tktechnologies.com.br/`. Added the same values
  to Bicep so future deployments preserve the custom URL.
- Audited custom DNS for `automacao.tktechnologies.com.br`: Azure Container Apps
  custom hostname binding and managed certificate are succeeded, public DNS
  returns `A 20.41.55.44`, and `asuid.automacao` TXT matches the Container Apps
  verification ID. If a browser still reports DNS not found, the remaining cause
  is client/ISP negative DNS cache or resolver propagation, not Azure binding.
- Extended `scripts/inspect_scrape_db.py` with `--audit` for read-only
  persistence integrity checks covering job/site status counts, orphan rows, and
  required result-field validity.
- Deployed `cdpscraperprodacr.azurecr.io/cdp-scraper:melibox-blocked-20260514-0135`
  to both production Container Apps after Melibox fixes. The scraper now uses
  the app origin for login even when `CREDENTIAL_MELIBOX_URL` points at
  `/advProductPosition`, clears stale stored browser state before one login
  retry, and maps login-entry 403/access blocks to `blocked` instead of generic
  `Authentication failed`.
- Re-ran the production curl smoke suite and refreshed
  `docs/validation/latest_production_curl_smoke.json`. Passing cases: API
  health, N8N health, GM, VW, EU Imports, and Peça Direta. Failing source cases:
  Mercado Livre returned `not_found` for `06K907811B`; Melibox returned
  `blocked` for `51766536` with `Melibox login entry returned 403/access block`.
- Consolidated scraper parser/status tests into the canonical
  `tests/test_scrapers/` package and removed tracked files from `tests/scrapers/`.
- Ran a production Azure audit against resource group `automation`. The scraper
  API, Celery worker, N8N, Redis, PostgreSQL, Key Vault, ACR, Container Apps
  environment, and Log Analytics resources exist in the expected regions and
  Container App revisions are healthy.
- Fixed the production Celery worker database failure seen in logs as
  `asyncpg.exceptions.InterfaceError: cannot perform operation: another operation
  is in progress` by disabling SQLAlchemy async connection pooling with
  `NullPool` when `JOB_EXECUTION_BACKEND=celery`.
- Normalized Azure async PostgreSQL URLs for SQLAlchemy/asyncpg by moving
  `ssl` / `sslmode` URL flags into `connect_args={"ssl": True}`. This keeps
  Key Vault `database-url` usable by the app and by local audit tooling.
- Built and deployed `cdpscraperprodacr.azurecr.io/cdp-scraper:audit-20260514-0055`
  to both `cdp-scrapers-api-prod` and `cdp-scrapers-worker-prod`.
- Verified production `/api/v1/lookup` through curl after deployment. VW SKU
  `5U6867287Y20` returned `success`, one exact BRL-priced result, and persisted
  to Azure PostgreSQL.
- Ran the initial production curl smoke manifest after the audit image. Passing
  cases: API health, N8N health, GM, VW, EU Imports, and Peça Direta. Failing
  source cases: Mercado Livre returned `not_found` for `06K907811B`; Melibox
  initially returned `Authentication failed` before the follow-up blocked-status
  deployment.
- Confirmed Azure PostgreSQL persistence after smoke testing: 11
  `scrape_jobs`, 4 `scrape_items`, and 3 `part_results` existed at audit time.
  Older pending jobs remain from pre-fix worker failures and should be cleaned
  up by an explicit operational retry/dead-letter task.
- Recorded production warnings to follow up: Redis Celery TLS is configured with
  `ssl_cert_reqs=CERT_NONE`; proxy rotation is enabled while `PROXY_URLS` is
  empty; VW logs show CEP modal setup failures before a successful search; Peça
  Direta's raw title for the current positive row is low quality (`Minha
  localização`).

## 2026-05-13
- Updated Azure production IaC and deployment automation for the clean rebuild
  target: PostgreSQL in Brazil South; ACR, Redis, Key Vault, Log Analytics,
  API, worker, and N8N in East US 2; separate scraper API and Celery worker
  Container Apps; N8N Container App; Key Vault storage for API/callback,
  database, Redis/Celery, Melibox, proxy, and N8N secrets; and a two-phase
  deploy script with `alembic upgrade head` before app rollout.
- Added `docs/AZURE_REBUILD_PLAN.md` for the clean Azure rebuild target:
  PostgreSQL in Brazil South, all other services in East US 2, API + Celery
  worker + N8N Container Apps, Redis-backed Celery, and Key Vault-only secret
  handling. Added `.claude/prompts/azure-production-rebuild.md` for starting a
  fresh deployment agent context.
- Added `scripts/production_scraper_curl_smoke.py` and
  `docs/validation/production_scraper_curl_cases.example.json` to repeatedly
  validate production `/api/v1/lookup` with curl for all active scrapers, plus
  optional N8N health.
- **Melibox:** fixed the live `advProductPosition` flow by selecting the
  **Frase/Palavra** input via `#textoPesquisa` and parsing prices from the
  table `R$` column when cells contain bare Brazilian amounts like `568,83`.
  Live SKU `51766536` now returns `success` with 17 exact BRL-priced rows in
  `docs/validation/latest_melibox_success_live_test.json`.
- **Archived Procura Peças and eBay** from the active registry (with GoParts): moved
  `ProcuraPecasScraper` and `EbayScraper` to `ARCHIVED_SCRAPER_REGISTRY`, updated default
  job `sites` in `ScrapeJobRequest`, validation manifest requirements, interview/demo
  runners, `run_scraper_case` choices, and docs. Parser tests for archived modules remain.
- **Peça Direta:** when listing cards show an exact part but **no price** on the card,
  open the `/produto/` page and re-extract; product-page JS now also reads `meta[itemprop="price"]`
  and `[itemprop="price"]` before falling back to body `R$` scan.
- **Melibox:** match SKU using row **text + link URL** (SKU often only in href); log table
  row count and warn when zero rows match after **Enviar**.
- **Interview demo:** default is **headed** (`PLAYWRIGHT_HEADLESS=false`) so the audience
  sees Chromium; `--headless` for CI/servers. `make interview-demo` sets headed explicitly.
- Added **interview terminal demo** (`scripts/interview_scraper_demo.py`): runs each
  production scraper sequentially with **field-guide SKUs** that more often return
  real prices, a **plain-language Rich layout** (big “best matching price”, sample
  table with “exact part?”, recap for non-developers), progress bar, and JSON output
  (`make interview-demo`). Aligned `scripts/demo_scraper_runs.py` default cases to the
  same SKUs. Added **DB inspector** (`scripts/inspect_scrape_db.py`, `make db-inspect`)
  for job/part_result counts and recent rows; documented that only API/orchestrator
  jobs persist to PostgreSQL, not the standalone demo. Dev dependency: `rich`.
  Makefile `lint` / preflight now include `scripts/`.
- Rebuilt the Melibox scraper around the authenticated **advProductPosition**
  flow: fill **Frase/Palavra** with the SKU, click **Enviar**, and parse BRL
  prices from listing rows (replacing generic `/anuncios` / `/produtos` URL
  fallbacks and broad card harvesting).
- Archived GoParts after repeated direct `/busca/{sku}` browser timeouts. The
  GoParts code and docs remain for reference, but it is removed from the active
  scraper registry, API defaults, demo choices, and local validation manifest.
- Added an authenticated Melibox/Sellerbox scraper baseline, config/env entries,
  registry wiring, demo/validation script support, parser tests, and Melibox
  source docs. The scraper uses source-specific SKU pacing and optional
  context rotation between SKUs when proxy rotation is enabled.
- Added `docs/SCRAPER_AGENT_PLAYBOOK.md`, per-source playbooks under
  `docs/scrapers/`, and `.claude/skills/scraper-source-playbooks.md` so future
  agents can work each scraper with source-specific context and validation
  discipline.
- Fixed GM Chevrolet details extraction for the current 2024 dealer-offer DOM:
  `.tab-precos-row-2024`, `.concessionaria-name-2024`, and
  `.concessionaria-preco-2024-value` now produce one result per dealer price.
- Fixed PeçaDireta search extraction so it only follows same-site `/produto/`
  URLs and preserves exact out-of-stock products as `no_price` instead of
  following pagination, social-media, or footer links.
- Fixed VW exact matching for priced cards by accepting SKU evidence in the
  product title or product URL when the card extraction already found the SKU.
- Added shared per-action scraper jitter settings and stronger blocked-page
  detection for Cloudflare/CAPTCHA/turnstile indicators.
- Captured live verification artifacts:
  `docs/validation/latest_browser_demo_results_targeted.json` and
  `docs/validation/latest_all_scrapers_sku_probe.json`.

## 2026-05-12
- Added the root `demo` runner for headed browser demos across the in-scope
  scrapers, with step-by-step console output and per-case JSON results.
- Clarified the shared site status vocabulary to include `blocked` in schema
  help text, specs, manual validation docs, and the scraper field guide.
- Added headed one-case scraper validation via `scripts/run_scraper_case.py`,
  with `PLAYWRIGHT_SLOW_MO_MS` support and recorded results in
  `docs/validation/latest_headed_scraper_results.json`.
- Added shared `no_price` site status semantics: exact product found without a
  positive price now returns `no_price`; non-exact marketplace candidates no
  longer make a site status `success`.
- Fixed GM headed validation by submitting the visible CEP modal/header control
  instead of selecting hidden/default CEP elements.
- Fixed PeçaDireta exact SKU detection for product title/path matches without a
  visible price, so the live `06K907811B` case returns `no_price`.
- Fixed eBay marketplace price parsing for BRL values rendered with US-style
  decimal separators.
- Made SQLite test database configuration explicit and skipped PostgreSQL-only
  pool options for SQLite async engines.
- Added scraper validation docs in `docs/SCRAPER_MANUAL_VALIDATION.md` and
  focused scraper tests, now consolidated under `tests/test_scrapers/`.
- Persisted per-site status snapshots for each scraped SKU so DB-backed job reads preserve `success`, `not_found`, and `error` site results even when a site returned no parts.
- Removed the GM scraper's custom browser initialization so it uses the shared BaseScraper lifecycle, including proxy rotation and configured `PLAYWRIGHT_HEADLESS` behavior.
- Made GM mock fallback explicit via `MOCK_SCRAPERS=true`; empty GM credentials no longer force the public GM scraper into mock mode.
- Clarified GoParts headless behavior: it uses the shared Playwright setting, with `PLAYWRIGHT_HEADLESS=false` reserved for manual validation when Cloudflare requires it.
- Added `scripts/demo_scraper_runs.py` and captured live scraper demo output in `docs/validation/latest_scraper_demo_results.json`.
- Added `docs/SCRAPER_FIELD_GUIDE.md`, `.claude/skills/scraper-field-work.md`, and `.claude/CLAUDE.md` so future agents have scraper-specific operating knowledge.
- Added Celery/Redis production job execution with a separate worker task path and `JOB_EXECUTION_BACKEND=celery`.
- Kept local in-process job execution as the development/test default via `JOB_EXECUTION_BACKEND=local`.
- Updated Docker Compose, Makefile, environment templates, and production docs for API + Celery worker operation.
- Clarified that inbound tool-specific webhook routes are removed; external systems should call `/api/v1/jobs` and use `callback_url` for completion notifications.
- Fixed `best_price` aggregation so the service no longer compares priced exact matches across mixed currencies without an explicit conversion layer.
- Added focused tests covering same-currency best-price selection and mixed-currency suppression in the orchestrator path.
- Fixed Alembic CLI imports by adding the project root to `sys.path` in `alembic/env.py`.
- Added local real-scraper validation tooling, a gitignored manifest workflow, and Makefile targets for Docker DB reset, preflight checks, and scraper validation.
- Added initial Bicep modules for ACR, Container Apps, PostgreSQL, Redis, Key Vault, managed identity, and optional proxy pool.

## 2026-05-11
- Moved current and legacy workflow-automation handoff files to `/tmp/cdp-workflow-handoff`.
- Removed workflow-automation-specific docs, local Docker service, env vars, and webhook route from the scraper project.
- Replaced workflow-specific callback settings with generic `CALLBACK_WEBHOOK_SECRET`.
- Updated scraper docs and specs to describe generic external callback contracts instead of owning automation workflow files.
- Added a reusable new-chat startup prompt for AI maintenance agents at `.claude/prompts/agent-startup.md`.
- Added documentation maintenance rules at `docs/SPECS/DOC_MAINTENANCE_SPEC.md`.
- Aligned `.claude` references with the current `docs/SPECS/` source-of-truth directory.
- Fixed the scraper registry duplicate VW import and duplicate `SiteId.VW` registry entry.
- Documented that fresh agents must audit the project, update docs with code changes, run focused tests, and suggest improvements.
- Applied all critical findings from the project audit (F-01 through F-13), including:
  - Fixed test suite isolation by using SQLite for orchestrator tests.
  - Generated initial Alembic baseline migration after adding `psycopg2-binary`.
  - Resolved 14 Ruff linting violations and removed deprecated `datetime.utcnow()`.
  - Aligned site credential settings and missing templates in `.env.example` and `.env.production.example`.
  - Cleaned up Dockerfile references, stale markdown files, and obsolete queue code before the Celery/Redis production path was reintroduced.
