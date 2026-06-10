# IPRoyal ISP proxy — setup runbook (CDP scrapers)

Use this guide when you buy **IPRoyal ISP proxies** (static residential / ISP) to test
Brazilian egress for Melibox and other suppliers. It connects IPRoyal’s dashboard to
our scraper configuration.

**Related (platform-agnostic):**

| Doc | Purpose |
|-----|---------|
| [PROXY_ROTATION_SPEC.md](../SPECS/PROXY_ROTATION_SPEC.md) | How the scraper uses proxies |
| [.agent/workflows/proxy-rollout.md](../../.agent/workflows/proxy-rollout.md) | Phased rollout checklist |
| [.agent/commands/proxy-readiness.md](../../.agent/commands/proxy-readiness.md) | Readiness command |
| [MAINTENANCE_CHECKPOINT.md](../MAINTENANCE_CHECKPOINT.md) | Current production snapshot |

**IPRoyal docs (external):**

- [ISP proxy strings](https://docs.iproyal.com/proxies/isp/using-proxy-strings)
- [ISP quick start](https://iproyal.com/quick-start-guides/static-residential-proxies/)

---

## 1. What to buy on IPRoyal

| Choose | Avoid (for this test) |
|--------|------------------------|
| **ISP Proxies** (static residential / ISP) | Datacenter proxies |
| **Country: Brazil** | US/EU-only orders |
| **1 dedicated IP** to start | Large rotating residential pools |
| **HTTP\|HTTPS** protocol in the order panel | SOCKS5 for first rollout (we validate HTTP first) |

Why: Azure blocks Melibox on **datacenter** egress. You need a **Brazilian ISP-assigned**
IP with a stable session, not a new IP on every request.

Default IPRoyal ports (confirm in your **Formatted Proxy List**):

- HTTP/HTTPS: often `12323`
- SOCKS5: often `12324` (use only after HTTP path works)

---

## 2. Copy credentials from IPRoyal

1. Open your order → **Order Configuration**.
2. Set **Protocol** to **HTTP|HTTPS** and note the **Port**.
3. Open **Formatted Proxy List** — copy the line for your BR IP.

You need four values:

- `HOST` — proxy IP (Brazil)
- `PORT` — e.g. `12323`
- `USERNAME`
- `PASSWORD`

Build the URL our app expects (one line, no spaces):

```text
http://USERNAME:PASSWORD@HOST:PORT
```

Example shape (not real credentials):

```text
http://myuser:mypass@191.116.125.248:12323
```

If the password contains `@`, `#`, or `%`, URL-encode it or change credentials in
IPRoyal (allowed about once per hour per their FAQ).

Optional sanity check with curl (from your laptop):

```bash
curl -x "http://USERNAME:PASSWORD@HOST:PORT" -L https://api.ipify.org?format=json
```

The returned `ip` must match the IP shown in IPRoyal for that proxy.

---

## 3. Local validation (before Azure)

From the repo:

```bash
cd scrapers
make setup   # if needed

# Step A — proxy + Playwright only (no supplier sites)
uv run python scripts/proxy_readiness_check.py \
  --proxy-url 'http://USERNAME:PASSWORD@HOST:PORT'
```

**Pass:** `playwright=ok` and `egress_ip` equals your IPRoyal IP.

```bash
# Step B — supplier smoke (Melibox first)
export PROXY_ROTATION_ENABLED=true
export PROXY_FAIL_CLOSED=true
export PROXY_AFFINITY_ENABLED=true
export PROXY_STATE_PER_IDENTITY=true
export PROXY_URLS='["http://USERNAME:PASSWORD@HOST:PORT"]'

# Melibox needs real credentials in scrapers/.env (never commit)
# CREDENTIAL_MELIBOX_USER=...
# CREDENTIAL_MELIBOX_PASS=...

uv run python scripts/proxy_site_smoke.py --from-env
```

**Pass criteria:**

| Site | Target |
|------|--------|
| `melibox` | `success` with priced rows (main goal) |
| `gm`, `vw`, `eu`, `pecadireta`, `ml` | `success` or known `not_found` — no new `blocked` |
| `goparts`, `procurapecas` | Optional: `--include-archived` — Cloudflare may still `blocked` |

Report file: `docs/validation/latest_proxy_site_smoke.json`

**Best practices during testing:**

- Keep `MAX_CONCURRENT_SCRAPERS=1` and `SCRAPE_SITES_SEQUENTIAL=true`.
- Leave `MELIBOX_ROTATE_CONTEXT_PER_SKU=false` until Melibox is stable.
- Do not delete `browser_states/` mid-session; if you change proxy IP, remove old
  `*_state.json` files so cookies are not reused across identities.
- Run one site at a time when debugging:  
  `uv run python scripts/proxy_site_smoke.py --site melibox --sku 51766536`

---

## 4. Configure production (Azure Key Vault)

Secret name used by Bicep / Container Apps: **`proxy-urls`**

Value must be a **JSON array** with one URL string (same as local):

```json
["http://USERNAME:PASSWORD@HOST:PORT"]
```

Example CLI (replace vault name and values; run from a secure shell):

```bash
KEY_VAULT_NAME=cdp-scrapers-kv-prod
PROXY_JSON='["http://USERNAME:PASSWORD@HOST:PORT"]'

az keyvault secret set \
  --vault-name "$KEY_VAULT_NAME" \
  --name proxy-urls \
  --value "$PROXY_JSON"
```

Ensure Container Apps already map:

- `PROXY_URLS` → secret ref `proxy-urls`
- `PROXY_ROTATION_ENABLED=true`
- `PROXY_FAIL_CLOSED=true` (worker **will not start** if rotation is on and the secret is empty)

See `.env.production.example` for the full proxy + anti-bot block.

After setting the secret:

1. Deploy or restart **both** `cdp-scrapers-api-prod` and `cdp-scrapers-worker-prod`.
2. Exec/readiness from a context that sees prod env, or submit one Melibox job via API.
3. Confirm outbound IP in IPRoyal traffic/logs matches the purchased IP.

**Do not** commit proxy URLs, `.env` with secrets, or smoke JSON containing credentials.

---

## 5. Enable Melibox in production jobs

Melibox is **not** in the router’s default site list. After Melibox smoke passes:

1. Set n8n / router env `CDP_SCRAPER_SITES` to include `melibox`, e.g.  
   `gm,ml,vw,eu,pecadireta,melibox`  
   (exact env name is in `n8n/src/formatar_payload_scraper.js` / `cdp_router`.)
2. **Publish n8n only with explicit team approval** (`make sync-n8n`).

Until then, test Melibox via direct API jobs with `"sites": ["melibox"]`.

---

## 6. Re-enable GoParts / Procura Peças (only if smoke says so)

Code for archived sites remains in the repo. **Do not** move them back to
`SCRAPER_REGISTRY` until `proxy_site_smoke.py` shows acceptable status with
`--include-archived`.

Cloudflare Turnstile may still block headless Playwright even with a BR ISP IP.
If status stays `blocked` or `timeout`, see `docs/scrapers/goparts.md` and
`docs/scrapers/procurapecas.md` for API/alternate strategies.

---

## 7. Troubleshooting

| Symptom | Likely cause | Action |
|---------|----------------|--------|
| Worker crash on start | `PROXY_FAIL_CLOSED=true` and empty `PROXY_URLS` | Set Key Vault secret or disable rotation temporarily |
| Readiness OK, Melibox `blocked` | Wrong product (datacenter), wrong country, or site policy | Confirm ISP + Brazil in IPRoyal; verify Melibox credentials |
| Readiness fails Playwright | Wrong port (SOCKS vs HTTP), bad credentials | Use HTTP port from Formatted Proxy List |
| `egress_ip` ≠ IPRoyal IP | Proxy not applied | Check `PROXY_ROTATION_ENABLED` and JSON array format |
| Worked locally, fails in Azure | Stale `browser_states` or secret not on worker | New revision + clear states; verify worker secret ref |
| All sites `blocked` after enable | Concurrency too high | `MAX_CONCURRENT_SCRAPERS=1`, respect circuit breaker cooldown |

---

## 8. After a successful test

Update (no secrets):

- `scrapers/.agent/memory/implementation-state.md` — provider: IPRoyal ISP BR, date, Melibox result
- `../../.agent/memory/implementation-state.md` — same one-line note
- Mark proxy rollout complete in `docs/MAINTENANCE_CHECKPOINT.md`

Optional production checks:

```bash
API_BASE_URL=... API_KEY=... uv run python scripts/production_scraper_curl_smoke.py
uv run python scripts/test_production_5sku_cache_audit.py
```

---

## Quick reference — env vars

```bash
PROXY_ROTATION_ENABLED=true
PROXY_URLS='["http://USER:PASS@HOST:PORT"]'
PROXY_BYPASS=localhost,127.0.0.1
PROXY_FAIL_CLOSED=true
PROXY_AFFINITY_ENABLED=true
PROXY_STATE_PER_IDENTITY=true
MAX_CONCURRENT_SCRAPERS=1
SCRAPE_SITES_SEQUENTIAL=true
MELIBOX_ROTATE_CONTEXT_PER_SKU=false
```

Scripts:

```bash
uv run python scripts/proxy_readiness_check.py --proxy-url '...'
uv run python scripts/proxy_site_smoke.py --from-env
```
