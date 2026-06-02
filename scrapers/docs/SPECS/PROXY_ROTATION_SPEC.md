# Proxy Rotation Spec

## Goal
Give the scraper service controlled outbound network identity so browser-based
scrapers can use approved Brazilian ISP/static residential egress, keep
site/session history coherent, and later expand to a measured proxy pool.

This is not a guarantee against blocking. It is one layer alongside realistic
browser behavior, session persistence, lower request bursts, better selectors,
and source-specific rules.

## Application Behavior
The scraper app supports proxy rotation through:

- `PROXY_ROTATION_ENABLED`
- `PROXY_URLS`
- `PROXY_BYPASS`
- `PROXY_FAIL_CLOSED`
- `PROXY_AFFINITY_ENABLED`
- `PROXY_STATE_PER_IDENTITY`
- `ANTI_BOT_CIRCUIT_BREAKER_*`

Example:

```bash
PROXY_ROTATION_ENABLED=true
PROXY_URLS='["http://user:pass@br-isp-proxy.example:12323"]'
PROXY_BYPASS="localhost,127.0.0.1"
PROXY_FAIL_CLOSED=true
PROXY_AFFINITY_ENABLED=true
PROXY_STATE_PER_IDENTITY=true
```

`src/utils/proxy_manager.py` parses the URLs and returns Playwright-compatible proxy dictionaries.

`src/scrapers/base.py` assigns a stable proxy per site by default when a scraper
creates a browser context. With one ISP proxy, every site uses the same egress
IP. With multiple proxies, each site gets a consistent proxy until process
restart, avoiding cookie/session reuse across unrelated network identities.

When `PROXY_STATE_PER_IDENTITY=true`, browser state files include the non-secret
proxy identity, for example `ml_ab12cd34ef56_state.json`. This prevents cookies
created through one ISP/proxy from being reused through another.

Production scrapers should inherit that shared initialization path. If a scraper needs source-specific setup after the context is created, it should call `super().initialize()` first so proxy assignment, session state, and `PLAYWRIGHT_HEADLESS` remain consistent.

The same shared initialization path now also applies the browser anti-bot
profile:

- `BROWSER_LOCALE`, `BROWSER_TIMEZONE_ID`, and `BROWSER_ACCEPT_LANGUAGE` align
  the browser context with Brazilian operator traffic by default.
- `BROWSER_VIEWPORT_WIDTH` and `BROWSER_VIEWPORT_HEIGHT` keep a stable desktop
  viewport.
- `BROWSER_USER_AGENTS` accepts a JSON list for per-context user-agent rotation.
  When the list is empty, the scraper derives a Chromium-compatible Linux
  user-agent from Playwright's installed browser version instead of hardcoding an
  outdated browser string.
- `BROWSER_EXTRA_HTTP_HEADERS_ENABLED` controls the supplemental
  `Accept-Language` header. Chromium still supplies navigation-only headers
  such as `Upgrade-Insecure-Requests` itself; do not force those context-wide or
  XHR/API requests can look unnatural.
- `BROWSER_STEALTH_ENABLED` installs a small init script for low-risk browser
  automation signal cleanup.

During `scrape_sku()`, `BaseScraper` watches main-document HTTP status codes in
`ANTI_BOT_BLOCK_STATUS_CODES` (default `[403,429]`). When a block or visible
challenge page is detected, it waits with exponential jitter using
`ANTI_BOT_RETRY_ATTEMPTS`, `ANTI_BOT_BACKOFF_MIN_SECONDS`, and
`ANTI_BOT_BACKOFF_MAX_SECONDS`; if the block remains, the site result is
`blocked`, not `not_found`.

## Current Limitation
Scraper instances are cached in `src/scrapers/__init__.py`, so proxy assignment currently happens when a scraper instance initializes or resets.

This is good enough for a first release with multiple sites and restarts. For true per-SKU rotation, the next step is to move context creation closer to each `scrape_sku()` execution or add controlled context resets between SKU batches.

Do not enable aggressive per-SKU rotation for authenticated sources until the
source has been tested. Stable site/account affinity is safer for static ISP
proxies.

## Network Design
Preferred first rollout:

```text
Container App
  -> authenticated Brazilian ISP/static residential proxy
  -> supplier websites
```

Use an ISP/static residential provider first when the problem is IP reputation,
Brazilian locality, or supplier access policy. A cloud proxy pool can still be
useful for controlled egress, but cloud public IPs may not resolve blocks caused
by datacenter reputation.

For an Azure-managed proxy pool after the single-ISP baseline is stable, use:

- 1 virtual network.
- 1 subnet for proxy VMs.
- 2-3 Standard Static Public IPs.
- 2-3 small Linux VMs or VM Scale Set instances pinned to separate public IPs.
- 1 Network Security Group.
- 1 Key Vault secret for proxy credentials.
- Container App secrets for `PROXY_URLS`.

Recommended proxy software:
- Squid for a simple authenticated HTTP CONNECT proxy.
- Envoy if we later need richer telemetry and policy.

Start with Squid for Azure-managed proxies because it is simple, cheap, and
proven.

## Anti-Bot Operating Rules
- Keep browser state per site.
- Do not rotate IP in the middle of an authenticated session unless the target site tolerates it.
- Use one proxy per browser context/session.
- Reset sessions deliberately when rotating identity for authenticated sources.
- Keep request concurrency bounded by `MAX_CONCURRENT_SCRAPERS`.
- Use source-specific throttling; a larger proxy pool does not make unlimited scraping safe.
- Keep user-agent, locale, timezone, and persistent cookies coherent within the
  same browser context. Rotate identity only when creating a fresh context.
- Treat `403`, `429`, CAPTCHA, Cloudflare, Turnstile, and access-denied pages as
  `blocked` with observability, not as empty search results.
- `ANTI_BOT_CIRCUIT_BREAKER_*` pauses a site/proxy pair after repeated blocks so
  jobs stop hammering a challenged identity.

## Health Checks
Each proxy should support a validation command equivalent to:

```bash
curl -x http://user:pass@<proxy-ip>:3128 https://api.ipify.org
```

The returned IP must match the proxy public IP.

For the scraper runtime, validate both plain HTTP proxy connectivity and
Playwright browser-context proxying before running supplier checks:

```bash
uv run python scripts/proxy_readiness_check.py \
  --proxy-url 'http://user:pass@host:12323'
```

Use `--from-env` after setting `PROXY_ROTATION_ENABLED=true` and `PROXY_URLS`.
The readiness script only calls neutral IP echo endpoints; it does not probe
supplier websites.

## ISP / Static Residential Providers

Static ISP proxies such as IPRoyal/RoyalIP should be configured as ordinary
authenticated HTTP or SOCKS5 proxy URLs in `PROXY_URLS`. Prefer HTTP/HTTPS for
the first rollout because the scraper's helper script can validate it through
both `httpx` and Playwright; SOCKS5 should be validated through Playwright.

For static IPs, prefer site/session affinity over aggressive rotation:

- Keep one proxy per browser context.
- Reuse the same proxy for authenticated sessions unless a source-specific
  rule says otherwise.
- Reset browser state deliberately when changing IP for authenticated sites.
- Start with low concurrency and watch `blocked`, `403`, `429`, CAPTCHA, and
  timeout rates by site.

## Rollout Plan
1. Start with one validated Brazilian ISP/static residential proxy.
2. Store proxy credentials in Key Vault.
3. Set Container App secrets:
   - `proxy-urls`
   - `proxy-rotation-enabled`
   - optional circuit-breaker settings
4. Set env vars:
   - `PROXY_ROTATION_ENABLED=secretref:proxy-rotation-enabled`
   - `PROXY_URLS=secretref:proxy-urls`
   - `PROXY_FAIL_CLOSED=true`
   - `PROXY_AFFINITY_ENABLED=true`
   - `PROXY_STATE_PER_IDENTITY=true`
5. Restart the Container App revision.
6. Run one controlled scrape per site and confirm outbound IPs in proxy logs.
7. Keep `SCRAPE_SITES_SEQUENTIAL=true` and `MAX_CONCURRENT_SCRAPERS=1` until
   block rates are known.
8. Add more ISP proxies only after the single-proxy baseline is stable.

## Future Improvements
- Per-SKU context rotation.
- Proxy health scoring.
- Redis-backed circuit-breaker state if workers scale beyond one process.
