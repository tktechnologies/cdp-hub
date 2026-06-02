# Melibox Scraper

**Site ID:** `melibox`  
**Code:** `src/scrapers/melibox.py`  
**Source:** `https://melibox.com.br` / `https://app.melibox.com.br`

## Story

Melibox/Sellerbox is an authenticated Mercado Livre seller operations portal.
For CDP it is useful only when the account already has managed listings or
inventory rows that expose the exact automotive SKU. This is not a public
marketplace search; it depends on configured account credentials.

## What We Want

- Login through `https://app.melibox.com.br` (or the configured credential URL,
  which may redirect to login when unauthenticated).
- Open **`/advProductPosition`** (or use `CREDENTIAL_MELIBOX_URL` when it already
  points at that screen).
- Enter the SKU in **Frase/Palavra** and submit with **Enviar**.
- Read BRL prices from table rows that contain exact SKU evidence (normalized
  substring match in row text or product link).
- `no_price` when an exact SKU row exists without a positive price.
- `blocked` when access restriction, CAPTCHA, Cloudflare, or rate limiting is visible.

## Current DOM Map

Primary flow (implemented):

- Login: visible email/user input plus visible password input; submit
  Entrar/Login/Acessar/Continuar or Enter. When `CREDENTIAL_MELIBOX_URL`
  points directly at `/advProductPosition`, login still starts from the app
  origin (`https://app.melibox.com.br`).
- Work page: `CREDENTIAL_MELIBOX_URL` if it contains `advProductPosition`, else
  `{origin}/advProductPosition` derived from the configured app URL.
- Search: **Frase/Palavra** — primary live selector `#textoPesquisa`
  (`name="textoPesquisa"`), then `get_by_role` textbox name matching
  Frase/Palavra and scoped product-position text/search inputs.
- Submit: **Enviar** — button or submit input inside the product-position
  container, scoped to that section first; fallback Enter on the phrase field.
- Results: `table tbody tr` (and `[role='row']`) under `#advProductPosition` or
  `main`, skipping pure `<th>` header rows; prefer the table `R$` column cell
  (live index 5, values like `568,83`) before falling back to `R$ …` text scan.

## Anti-Bot Posture

- `MELIBOX_SKU_DELAY_MIN` / `MELIBOX_SKU_DELAY_MAX` add source-specific pacing
  before each SKU search.
- Keep `MELIBOX_ROTATE_CONTEXT_PER_SKU=false` for static ISP rollout so the
  authenticated account and browser state stay tied to one network identity.
- If rotation is explicitly enabled later, it happens between SKU searches, not
  inside an authenticated page flow.
- Do not add challenge-bypass logic. Detect access controls and return `blocked`.
- Before retrying login, the scraper removes stale stored browser state and
  clears cookies/session storage once. This prevents an expired or rejected
  state file from hiding the login page.

## Known Evidence

2026-05-13:

- Public site confirmed as `https://melibox.com.br`.
- Login link points to `https://app.melibox.com.br`.
- Authenticated `advProductPosition` live run for SKU `51766536` succeeded with
  17 exact rows and BRL prices.
- Local smoke confirms the scraper fails closed with `Authentication failed`
  when credentials are blank.

2026-05-14:

- Production Key Vault secrets `melibox-user` and `melibox-pass` are enabled and
  non-empty; API and worker Container Apps expose `CREDENTIAL_MELIBOX_USER`,
  `CREDENTIAL_MELIBOX_PASS`, and `CREDENTIAL_MELIBOX_URL`.
- Image `cdpscraperprodacr.azurecr.io/cdp-scraper:melibox-blocked-20260514-0135`
  returns `blocked` for production SKU `51766536` because
  `https://app.melibox.com.br` returns visible `403 forbidden` from the Azure
  worker before credentials can be submitted. The latest production artifact is
  `docs/validation/latest_production_curl_smoke.json`.

## Failure Modes

- Missing credentials return `Authentication failed`.
- Production login-entry `403 forbidden` returns `blocked` with
  `Melibox login entry returned 403/access block`.
- Stored browser state may expire or be rejected after IP rotation.
- Azure outbound IP or account/IP policy can block login before credentials are
  usable; resolve with approved proxy/IP allowlisting or account access changes.
- App DOM changes for **Frase/Palavra** or **Enviar** require headed selector
  updates in `src/scrapers/melibox.py`.
- **Zero rows after Enviar:** structured log `Melibox: candidate table rows` shows raw
  row count; if count > 0 but extraction is 0, the SKU may only appear in link `href`
  (now merged into matching) or the table uses a non-`<tr>` layout — capture headed DOM.

## Agent Moves

- Populate `CREDENTIAL_MELIBOX_USER` and `CREDENTIAL_MELIBOX_PASS` locally or
  through Azure secrets before live validation.
- Run headed first:

```bash
UV_CACHE_DIR=/tmp/uv-cache MELIBOX_SKU_DELAY_MIN=0 MELIBOX_SKU_DELAY_MAX=0 \
  uv run --extra dev python scripts/run_scraper_case.py \
  --site melibox --sku REPLACE_WITH_ACCOUNT_SKU --timeout-seconds 120 \
  --slow-mo-ms 350 --hold-seconds 10
```

- Capture only selectors and statuses in docs. Do not commit screenshots,
  browser state, cookies, or account data.
