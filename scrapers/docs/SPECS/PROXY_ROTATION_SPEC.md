# Proxy Rotation Spec

## Goal
Give the scraper service three independent outbound IP addresses so browser-based scrapers can rotate network identity and reduce anti-bot correlation.

This is not a guarantee against blocking. It is one layer alongside realistic browser behavior, session persistence, lower request bursts, better selectors, and source-specific rules.

## Application Behavior
The scraper app supports proxy rotation through:

- `PROXY_ROTATION_ENABLED`
- `PROXY_URLS`
- `PROXY_BYPASS`

Example:

```bash
PROXY_ROTATION_ENABLED=true
PROXY_URLS='["http://user:pass@20.1.2.3:3128","http://user:pass@20.1.2.4:3128","http://user:pass@20.1.2.5:3128"]'
PROXY_BYPASS="localhost,127.0.0.1"
```

`src/utils/proxy_manager.py` parses the URLs and returns Playwright-compatible proxy dictionaries.

`src/scrapers/base.py` assigns the next proxy in round-robin order when a scraper creates a browser context.

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

## Azure Design
Use three authenticated HTTP CONNECT proxies on Azure:

```text
Container App
  -> proxy-01 public IP
  -> proxy-02 public IP
  -> proxy-03 public IP
  -> supplier websites
```

Recommended resources:
- 1 virtual network.
- 1 subnet for proxy VMs.
- 3 Standard Static Public IPs.
- 3 small Linux VMs or VM Scale Set instances pinned to separate public IPs.
- 1 Network Security Group.
- 1 Key Vault secret for proxy credentials.
- Container App secrets for `PROXY_URLS`.

Recommended proxy software:
- Squid for a simple authenticated HTTP CONNECT proxy.
- Envoy if we later need richer telemetry and policy.

Start with Squid because it is simple, cheap, and proven.

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

## Health Checks
Each proxy should support a validation command equivalent to:

```bash
curl -x http://user:pass@<proxy-ip>:3128 https://api.ipify.org
```

The returned IP must match the proxy public IP.

## Rollout Plan
1. Deploy three Azure proxy endpoints.
2. Store proxy credentials in Key Vault.
3. Set Container App secrets:
   - `proxy-urls`
   - `proxy-rotation-enabled`
4. Set env vars:
   - `PROXY_ROTATION_ENABLED=secretref:proxy-rotation-enabled`
   - `PROXY_URLS=secretref:proxy-urls`
5. Restart the Container App revision.
6. Run one controlled scrape per site and confirm outbound IPs in proxy logs.
7. Increase concurrency gradually.

## Future Improvements
- Per-SKU context rotation.
- Site-specific proxy affinity.
- Proxy health scoring.
- Automatic temporary quarantine after HTTP 403/429/CAPTCHA spikes.
- Metrics by proxy endpoint and site.
