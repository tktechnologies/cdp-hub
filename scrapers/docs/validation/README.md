# Scraper validation artifacts

This directory holds **example manifests** and **generated audit outputs** for scraper validation scripts.

## Example manifests (tracked)

| File | Used by |
|------|---------|
| `local_scraper_manifest.example.json` | `scripts/validate_local_scrapers.py` |
| `production_scraper_curl_cases.example.json` | `scripts/production_scraper_curl_smoke.py`, `scripts/deploy-scraper-azure.sh` |

Copy an example to a local manifest (e.g. `*.local.json`) and fill in real SKUs before running validation.

## Generated outputs (gitignored)

Scripts write `latest_*.json` files here after audits and smoke runs. These are local evidence only — do not commit.

Examples: `latest_production_curl_smoke.json`, `latest_proxy_site_smoke.json`, `latest_scraper_demo_results.json`.
