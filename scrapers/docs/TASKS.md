# CDP Scraper — Project Status & Tasks

**Last Updated:** 2026-06-02  
**Status:** Production Azure stack live. Scrape cache validated. Active sites OK
except Melibox (`blocked` on Azure egress). **P0:** configure BR ISP proxy in Key
Vault — see `docs/MAINTENANCE_CHECKPOINT.md` and `.agent/workflows/proxy-rollout.md`.  
**Handoff:** `docs/MAINTENANCE_CHECKPOINT.md`.

---

## ✅ Phase 1: Core Code Hardening
**Objective:** Harden the codebase for production (persistence, reliability, security).
- [x] 1.1 Wire orchestrator job persistence to PostgreSQL (replace in-memory dict)
- [x] 1.2 Create first Alembic migration + fix config to read env var
- [x] 1.3 Fix `/lookup` endpoint busy-wait → proper async with event
- [x] 1.4 Add retry logic with tenacity to BaseScraper.scrape_sku()
- [x] 1.5 Wire Prometheus metrics into scraper + orchestrator flows
- [x] 1.6 Restrict CORS to configured origins
- [x] 1.7 Run focused tests for changed areas before handoff
- [x] 1.8 Prevent cross-currency `best_price` selection without explicit conversion
- [x] 1.9 Fix Alembic CLI import path for local migration checks

## ✅ Phase 3: Mock Testing (Moved ahead of Phase 2)
**Objective:** Enable E2E testing without real GM credentials.
- [x] 3.1 Create MockGMScraper with realistic fake data (no browser needed)
- [x] 3.2 Registry fallback: use mock only when MOCK_SCRAPERS=true
- [x] 3.3 E2E integration test: submit job → poll → verify DB results

## ✅ Phase 4: Azure Infrastructure
**Objective:** Provision all Azure resources via CLI.
- [x] 4.1 Create Container Registry (`cdpscraperprodacr.azurecr.io`)
- [x] 4.2 Create PostgreSQL Flexible Server (`cdp-scrapers-pg-prod`, Brazil South)
- [x] 4.3 Create Redis Cache (`cdp-scrapers-redis-prod`, East US 2)
- [x] 4.4 Create Key Vault (`cdp-scrapers-kv-prod`, East US 2)
- [x] 4.5 Create Container App environment (`cdp-scrapers-prod-env`, East US 2)
- [x] 4.6 Create deployment script (scripts/deploy-azure.sh)

---

## 🚀 Phase 2: Real Scrapers (Back in Focus)
**Objective:** Implement real scrapers with production credentials.
- [x] 2.1 **Collect Credentials/Align** (Confirmed decisions from 23/02 meeting)
- [x] 2.2 **Receive Business Rules** (Client will send remaining rules as text)
- [x] 2.3 Implement **GM Scraper** against the public Peça Chevrolet portal
- [x] 2.4 Implement **Mercado Livre Scraper** (Completed)
- [x] 2.5 Implement **VW Scraper** (Completed)
- [x] 2.6 Implement **Europe Scraper** (Completed)
- [x] 2.7 Archive **GoParts** (browser flow timed out consistently; removed from active registry/defaults)
- [x] 2.8 Implement **Melibox/Sellerbox Scraper** (advProductPosition / Frase/Palavra / Enviar flow; live headed validation still pending credentials)

## 🔮 Phase 5: CI/CD & Operations
**Objective:** Automate testing and deployment.
- [x] 5.1 Add Celery/Redis production job execution backend
- [x] 5.2 Validate production API + Celery worker queue path with curl
- [ ] 5.3 Run local real-scraper validation with a populated manifest
- [x] 5.3a Run headed one-case real-scraper validation with the provided VW SKU set
- [x] 5.4 Validate Bicep build and Azure `what-if`
- [ ] 5.5 GitHub Actions CI (lint + test on PR)
- [x] 5.6 GitHub Actions CD (build + push ACR + deploy API + worker)
- [ ] 5.7 Production env template with Azure secrets
- [ ] 5.8 Slack/Teams alert integration
- [ ] 5.9 Azure Monitor dashboard
- [ ] 5.10 Add stuck-job/retry/dead-letter operational checks for Celery tasks
- [x] 5.11 Add clean Azure rebuild plan and production curl smoke script
- [x] 5.12 Update IaC/deploy scripts for clean rebuild: PostgreSQL Brazil South, all other services East US 2, API + worker + N8N
- [x] 5.13 Run production curl smoke tests for all active scrapers after deployment
- [x] 5.14 Fix production Celery asyncpg pooling failure with `NullPool`
- [x] 5.15 Normalize asyncpg SSL URL handling for Azure PostgreSQL audit/runtime
- [x] 5.16 ML production curl smoke uses SKU `51766536` (`production_scraper_curl_smoke.py`)
- [ ] 5.17 Resolve Melibox production login-entry `403` (BR ISP proxy in Key Vault + `proxy_site_smoke.py`)
- [x] 5.17a Add shared anti-bot browser profile, HTTP block detection, and
      bounded backoff before reporting `blocked`
- [x] 5.17b Fix demo fallout from anti-bot headers/timing: keep
      `Upgrade-Insecure-Requests` browser-owned, slow the interview demo, and
      wait for GM dealer-price rows before extraction
- [x] 5.17c Update local demo/test SKU map for all sources, including
      demo-only archived sources: GoParts, Procura Peças, and eBay
- [x] 5.17d Add ISP-proxy affinity, proxy-specific browser state, block circuit
      breaker, safer production pacing, and proxy-aware HTTP preflight
- [ ] 5.18 Configure production `PROXY_URLS` in Key Vault — workflow: `.agent/workflows/proxy-rollout.md`
- [ ] 5.19 Harden Redis TLS validation for Celery instead of `ssl_cert_reqs=CERT_NONE`
- [x] 5.20 Deploy Melibox login-entry fix and explicit blocked-status reporting
- [x] 5.21 Bind and validate N8N custom DNS `automacao.tktechnologies.com.br`
      against the Container Apps static IP and verification TXT record
- [ ] 5.22 Move authoritative DNS management for `tktechnologies.com.br` or the
      `automacao` subdomain into Azure DNS to avoid HostGator/client resolver drift

## 🧭 Next System Checkup
**Objective:** Re-audit the whole scraper service after queue restoration and align code, tests, docs, and deployment.
- [x] C1 Run stale-reference audit and remove any remaining callback or queue drift
- [x] C2 Review API, worker, database, scraper, and callback flows against `docs/SPECS/SPECS.md`
- [ ] C3 Run targeted tests for API, orchestrator, queue submission, scrapers, and proxy manager
- [ ] C4 Validate Docker Compose with separate API and Celery worker processes
- [x] C5 Validate production env and Bicep/Container App worker deployment assumptions
- [x] C6 Update `docs/SYSTEM_OVERVIEW.md`, `docs/PRODUCTION_PLAN.md`, `README.md`, and changelog from findings

## 🧠 AI-Assisted Maintenance
**Objective:** Make every fresh agent session audit, align, document, and improve the scraper service.
- [x] A1 Create source-of-truth specs under `docs/SPECS/`
- [x] A2 Create reusable new-chat startup prompt at `.agent/prompts/agent-startup.md`
- [x] A3 Add documentation maintenance contract at `docs/SPECS/DOC_MAINTENANCE_SPEC.md`
- [x] A4 Add project changelog at `docs/CHANGELOG.md`
- [x] A5 Add `.agent/commands/start-maintenance-chat.md`
- [x] A6 Fix duplicate VW scraper registry entry
- [x] A7 Move workflow-automation handoff files to `/tmp/cdp-workflow-handoff`
- [x] A8 Remove workflow-automation-specific docs/config/routes from scraper repo
- [x] A9 Replace legacy agent-directory guidance with `.agent/rules.md`
- [x] A10 Add Bicep infrastructure modules for Azure resources and proxy pool
- [ ] A11 Add per-SKU or per-batch proxy context rotation when production proxy endpoints are ready
- [x] A12 Add scraper field guide, live demo runner, and scraper field-work skill
- [x] A13 Add headed one-case scraper validation runner and manual runbook
- [x] A14 Add shared `no_price` site status semantics and parser/status tests
- [ ] A15 Curate positive SKU fixtures for GM, VW Official, and Procura Peças
- [x] A16 Add headed root `demo` runner with per-case JSON output
- [x] A17 Fix GM dealer prices, PeçaDireta product-link filtering, and VW exact priced matching
- [x] A18 Archive GoParts after repeated live timeouts
- [x] A19 ProcuraPeças/eBay archived from active registry (2026-05-13); code retained for reference
- [x] A20 Add per-scraper agent playbooks and scraper-source skill
- [x] A21 Consolidate scraper parser/status tests under `tests/test_scrapers/`
- [ ] A22 Validate Melibox headed flow with real credentials and a known account SKU from an allowed network/IP
- [x] A23 Align `.agent/` prompts, rules, commands, skills, workflows, and
      settings with the current CDP scraper architecture
- [x] A24 Add shared anti-bot controls to `BaseScraper` and document the
      browser profile / retry / proxy operating rules
- [x] A25 Add Redis 24h per-site SKU scrape cache with PostgreSQL fallback
      (`src/services/scrape_cache.py`, orchestrator + `/lookup` integration)
- [x] A26 Deploy `SCRAPE_CACHE_*` env vars to Azure API and worker Container Apps
      (image `scrape-cache-ssl-20260521-1402`; production smoke PASS)
- [x] A27a Validate production `/lookup` + `/jobs` cache with 5-SKU audits and
      E2E batch job (`docs/validation/latest_production_5sku_*`, `latest_5sku_e2e_*`)
- [x] A27b n8n MCP read-only audit — live vs repo drift documented
      (`n8n/docs/AUDIT_2026-05-21.md`)
- [x] A27c Add `scripts/production_sku_pool.py` — random 5-SKU samples for audits
- [x] A27 Deploy API+worker image with `src/config.py` credential strip (fixes
      automated n8n callbacks; E2E job `86f8b3a4-...`, n8n execution 369)
- [x] A28 Publish repo `cdp_analise` / `cdp_resultado` to live n8n (2026-05-21;
      active versions aligned with repo contract via MCP SDK publish)
- [ ] A29 Trim Key Vault `callback-webhook-secret` or confirm strip-only via deploy
