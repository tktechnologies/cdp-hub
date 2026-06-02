# CDP Scraper — Production Readiness Plan

## Current Status: Production Azure Stack Live (2026-05-21)

**Handoff:** `docs/MAINTENANCE_CHECKPOINT.md`

**✅ Completed:**
- Phase 1, 3, 4 (core hardening, mock tests, Azure infra)
- Production queue: API + Celery worker + Redis + PostgreSQL
- Scrape cache deployed and validated (`/lookup` + `/jobs`, 5-SKU audits)
- n8n MCP audit documented (`n8n/docs/AUDIT_2026-05-21.md`)

**🔄 In Progress:**
- Deploy credential strip for automated n8n callbacks (A27)
- Live n8n publish from repo exports when approved (A28)
- Melibox 403, ML smoke SKU, proxy URLs, Redis TLS hardening

**⏭️ Next (priority):**
1. Deploy worker/API with `src/config.py` secret strip — restores callbacks.
2. User-approved n8n workflow publish — align live with repo contract.
3. Melibox production access / proxy path; refresh ML positive smoke SKU.
4. Azure Monitor alerts; stuck-job cleanup; Redis `CERT_NONE` → validated TLS.

---

## Executive Summary

### What's Been Accomplished

**Phase 1 - Code Hardening (100%)**
- Database persistence with PostgreSQL (all jobs/results persisted)
- Async event-based job completion (no busy-wait)
- Retry logic with exponential backoff (3 attempts)
- CORS security restrictions
- **All tests passing**

**Phase 3 - Mock Testing (100%)**
- `MockGMScraper` implemented for credential-free testing
- Full E2E tests verifying the entire pipeline logic
- `MOCK_SCRAPERS=true` toggle for local dev

**Phase 4 - Infrastructure (100%)**
- Azure Container Registry: `cdpscraperprodacr.azurecr.io` ✅
- PostgreSQL Flexible Server: `cdp-scrapers-pg-prod.postgres.database.azure.com` ✅
- Key Vault: `cdp-scrapers-kv-prod` ✅
- Container App Environment: `cdp-scrapers-prod-env` ✅
- Scraper API Container App: `cdp-scrapers-api-prod` ✅
- Celery Worker Container App: `cdp-scrapers-worker-prod` ✅
- N8N Container App: `cdp-n8n-prod` ✅
- Redis Cache: `cdp-scrapers-redis-prod.redis.cache.windows.net` ✅
- Deployment Script: `scripts/deploy-azure.sh` ✅
- Proxy rotation app settings and round-robin manager ✅
- Celery/Redis production queue path ✅

## Production Audit - 2026-05-14

Validated live image:

```text
cdpscraperprodacr.azurecr.io/cdp-scraper:melibox-blocked-20260514-0135
```

Live health:
- `cdp-scrapers-api-prod`: running and healthy, `/api/v1/health` returns `200`.
- `cdp-scrapers-worker-prod`: running and healthy on the Celery worker command.
- `cdp-n8n-prod`: running and `/healthz` returns `200`.
- N8N custom domain `automacao.tktechnologies.com.br` is bound to
  `cdp-n8n-prod`, has a succeeded managed certificate, and resolves publicly to
  the Container Apps environment static IP `20.41.55.44`.
- Azure PostgreSQL persistence verified through `scripts/inspect_scrape_db.py`.

Database snapshot after the audit:
- `scrape_jobs`: 11
- `scrape_items`: 4
- `part_results`: 3
- Latest verified job: VW `5U6867287Y20`, status `completed`, `items_succeeded=1`, `items_failed=0`.

Production smoke results:
- Passing: API health, N8N health, GM `22781768`, VW `5U6867287Y20`, EU `06K907811B`, Peça Direta `06K907811B`.
- Failing: Mercado Livre `06K907811B` returned `not_found`; Melibox `51766536`
  returned `blocked` with `Melibox login entry returned 403/access block`.

Fixes deployed during audit:
- Celery worker database sessions now use `NullPool` when `JOB_EXECUTION_BACKEND=celery`, avoiding asyncpg connection reuse across worker task event loops.
- Async PostgreSQL URLs now normalize Azure `ssl` / `sslmode` query flags into asyncpg `connect_args`.
- Melibox login now starts from the app origin when the configured URL points at
  `/advProductPosition`, clears stale browser state before one login retry, and
  reports production login-entry 403/access blocks as `blocked`.

Operational warnings:
- Browser clients may still show DNS-not-found until their resolver clears an
  earlier negative cache for `automacao.tktechnologies.com.br`. Authoritative
  HostGator records are currently correct, but Azure DNS ownership would make
  future custom-domain operations more deterministic.
- Redis/Celery logs warn that `ssl_cert_reqs=CERT_NONE` disables broker certificate validation.
- Proxy rotation is enabled but production `PROXY_URLS` is empty.
- Old `pending` jobs remain from worker failures before the 2026-05-14 fix.
- VW logs show CEP modal setup failures before successful extraction.
- Peça Direta still returns weak `raw_title` text for the positive product page.

---

## Deployment Readiness

### Prerequisites (✅ All Met)
- [x] Azure subscription authenticated
- [x] Resource group `automation` exists
- [x] All infrastructure provisioned
- [x] Database schema created
- [x] Tests passing
- [x] Deployment script ready

### Immediate Next Steps

1. **Repair failing production smoke sources:**
   - Mercado Livre: find a currently positive exact SKU or update selectors.
   - Melibox: resolve the production `403 forbidden` at the login entry through
     an allowed outbound IP/proxy or account/IP access policy.

2. **Clean queue state:**
   - Add an explicit stuck-job/retry/dead-letter operational task.
   - Decide whether to mark pre-fix `pending` jobs failed or retry them.

3. **Deploy to Azure after code changes:**
   ```bash
   ./scripts/deploy-azure.sh
   ```

   Production must deploy both:
   - API process: `uvicorn src.main:app --host 0.0.0.0 --port 8000`
   - Worker process: `celery -A src.celery_app.celery_app worker --loglevel=INFO --concurrency=1`

4. **Verify Deployment:**
   ```bash
   curl https://<app-url>/api/v1/health
   ```

5. **Provision Proxy Egress:**
   - Start with one authenticated Brazilian ISP/static residential proxy.
   - Store `PROXY_URLS` as a Container App secret.
   - Set `PROXY_ROTATION_ENABLED=true`, `PROXY_FAIL_CLOSED=true`,
     `PROXY_AFFINITY_ENABLED=true`, and `PROXY_STATE_PER_IDENTITY=true`.
   - Validate each proxy with `curl -x http://user:pass@<proxy-host>:<port> https://api.ipify.org`.

---

## Detailed Implementation Plan

### ✅ Phase 1: Core Code Hardening (COMPLETE)
- **Database Persistence**: Replaced in-memory dict with PostgreSQL.
- **Async Job Waiting**: `/lookup` endpoint now properly async.
- **Retry Logic**: Added `tenacity` decorators.
- **Prometheus Metrics**: Scaffolding in place.
- **CORS**: Restricted to configured origins.

### ✅ Phase 3: Mock Testing (COMPLETE)
- **MockGMScraper**: Generates realistic dummy data.
- **Test Coverage**: Increased to confirm system stability before connecting to real sites.

### ✅ Phase 4: Azure Infrastructure (COMPLETE)
- **ACR**: `cdpscraperprodacr.azurecr.io`
- **PostgreSQL**: `cdp-scrapers-pg-prod`
- **Redis**: `cdp-scrapers-redis-prod`
- **Key Vault**: `cdp-scrapers-kv-prod`
- **Container Apps**: API, worker, and N8N are deployed.

### 🔄 Phase 2: Real Scrapers (IN PROGRESS)
**Files to Modify:**
- `src/scrapers/gm.py` (Public portal flow implemented; validate production CEP/session behavior)
- `src/scrapers/goparts.py` (Archived; not active)
- `src/scrapers/mercadolivre.py` (✅ Completed)
- `src/scrapers/vw.py` (✅ Completed)
- `src/scrapers/eu_imports.py` (✅ Completed)
- `src/scrapers/procurapecas.py` (Archived; not in registry — anti-bot / maintenance)
- `src/scrapers/ebay.py` (Archived; not in registry — access / CAPTCHA)
- `src/scrapers/melibox.py` (advProductPosition / Frase/Palavra / Enviar; validate with real credentials/account SKU)
- `.env` (Add API keys and credentials)

### ⏭️ Phase 5: CI/CD & Operations (PLANNED)
- **CI Pipeline**: GitHub Actions for lint/test.
- **CD Pipeline**: Auto-deploy to Container Apps on push.
- **Monitoring**: Connect Azure Monitor & set up Slack alerts.
- **IaC Pipeline**: Add Bicep validation/deployment workflow.
- **Worker Deployment**: Dedicated Celery worker Container App validated on 2026-05-14.
- **Proxy Observability**: Track scrape failures and block rates by proxy endpoint.

---

## Production Checklist

### Pre-Deployment
- [x] All tests passing
- [x] Database schema created
- [x] Infrastructure provisioned
- [x] Deployment script created
- [x] Proxy rotation application support added
- [x] Bicep module scaffold committed
- [x] Celery/Redis production queue code path added
- [x] Local validation runbook and manifest template added
- [ ] **Melibox Credentials Validated In Production**
- [ ] **Real scraper manifest populated and passed locally**
- [ ] **Mercado Livre Positive SKU Refreshed**
- [ ] **Three Azure proxy endpoints provisioned**
- [x] **Bicep `what-if` reviewed and approved**
- [x] **API + Celery worker deployed and tested as separate production processes**

### Post-Deployment
- [x] Health endpoint responding
- [x] Verify database writes
- [x] Check logs in Azure Container Apps
- [ ] Set up monitoring alerts

---

## Quick Reference

### Deploy to Azure
```bash
./scripts/deploy-azure.sh
```

### Run Tests Locally
```bash
# All tests (uses Mock Mode if no creds)
pytest tests/ -v
```

### Build Docker Image
```bash
docker build -t cdpscraperprodacr.azurecr.io/cdp-scraper:latest .
```
