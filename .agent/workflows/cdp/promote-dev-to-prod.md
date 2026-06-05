# Promote DEV → PRODUCTION

Run this checklist before merging `dev` → `main` and before **CD - Production**.

## Code quality

- [ ] Scraper: `make -C scrapers test lint`
- [ ] StokAPI: `make check-muvstok`
- [ ] If `contracts/` or callback payloads changed:
  - `cd scrapers && uv run pytest tests/test_contracts/ -v`
  - `cd muvstok-api && uv run pytest tests/test_contracts/ -v` (if present)

## DEV validation

- [ ] Push to `dev` and confirm **CD - Development** succeeded
- [ ] Optional smoke against DEV APIs (from repo root):
  - `make smoke-cache` only if pointed at DEV bases via env (default is production — override `CDP_SCRAPER_API_BASE` / StokAPI base first)
- [ ] DEV Telegram: `.sku` with 1 test SKU → rows on DEV sheets, callbacks on `dev-scraper-result` / `dev-muvstok-result`
- [ ] If n8n router/receiver code changed: `make sync-n8n-dev` on `dev` branch (IDs in GitHub `development` vars)

## Production deploy

- [ ] PR `dev` → `main` reviewed and merged
- [ ] GitHub **CD - Production** → `workflow_dispatch`
- [ ] Enable only needed steps: `deploy_scraper`, `deploy_stokapi_api`, `deploy_stokapi_worker`, `sync_n8n`
- [ ] `sync_n8n` only with explicit approval ([n8n-release-checklist.md](n8n-release-checklist.md))
- [ ] Post-deploy: prod Telegram or whitelisted email smoke
- [ ] Update `docs/n8n/LIVE_WORKFLOWS.md` and `.agent/memory/implementation-state.md` if n8n versions changed

## Do not

- Copy prod secrets into `cdp-scrapers-kv-dev`
- Give customers the DEV Telegram bot
- Run `make sync-n8n` without approval
