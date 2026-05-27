"""GoParts Brazil scraper — goparts.com.br.

- Site: https://goparts.com.br
- Search: URL-based  /busca/{SKU}
- No login required (public search aggregator)
- Results layout: table within div.list-of-parts
- Used by ALL 18 brands in the customer's Excel matrix

Key technical constraints:
- Site uses Cloudflare + heavy analytics (Hotjar, Facebook Pixel)
- Playwright hangs on DOM access if analytics scripts are loaded
- Must block tracking scripts via route interception
- Uses the shared Playwright headless setting; manual validation may require
  PLAYWRIGHT_HEADLESS=false if Cloudflare challenges headless sessions
- All DOM extraction via page.evaluate() to avoid Playwright timeouts

Key business rules:
- Price in BRL (R$ format)
- SKU searched as-is on BR site (no transformations)
- Results may include multiple sellers/dealers
"""

import asyncio
import contextlib
import random

import httpx
import structlog
from playwright.async_api import Page
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from src.config import settings
from src.models.schemas import Currency, ItemCondition, PartResult, SiteId
from src.scrapers.base import BaseScraper

logger = structlog.get_logger()

BASE_URL = "https://goparts.com.br"
SEARCH_URL = f"{BASE_URL}/busca"

# Tracking domains to block — they cause Playwright to hang on this site
BLOCKED_DOMAINS = [
    "hotjar.com",
    "connect.facebook.net",
    "facebook.com/tr",
    "google-analytics.com",
    "googletagmanager.com",
    "doubleclick.net",
    "clarity.ms",
    "googlesyndication.com",
    "adservice.google",
    "static.hotjar.com",
]


class GoPartsScraper(BaseScraper):
    """Scraper for GoParts Brazil automotive parts aggregator.

    This is a public aggregator site — no authentication required.

    IMPORTANT: GoParts has heavy analytics/tracking scripts (Hotjar, Facebook
    Pixel, Google Analytics) that cause Playwright to hang during DOM evaluation.
    This scraper blocks those scripts and uses page.evaluate() for extraction.

    Search flow:
        1. Navigate to /busca/{SKU}
        2. Wait for page settle
        3. Extract results via JS evaluate (avoids Playwright DOM timeouts)
    """

    @property
    def site_id(self) -> SiteId:
        return SiteId.GOPARTS

    @property
    def site_name(self) -> str:
        return "GoParts Brazil"

    @property
    def base_url(self) -> str:
        return BASE_URL

    async def initialize(self) -> None:
        """Start browser with analytics blocking for GoParts.

        Calls super().initialize() then adds route interception to block
        tracking/analytics scripts that make the page too heavy for Playwright.
        """
        await super().initialize()
        assert self._context is not None

        # Block tracking/analytics domains that cause Playwright to hang
        for domain in BLOCKED_DOMAINS:
            await self._context.route(
                f"**/*{domain}*",
                lambda route: route.abort(),
            )

        # Block images and fonts for faster page loads
        await self._context.route(
            "**/*.{png,jpg,jpeg,gif,svg,webp,ico,woff,woff2,ttf,eot}",
            lambda route: route.abort(),
        )

        logger.info("GoParts: analytics blocking enabled")

    async def login(self, page: Page) -> bool:
        """No authentication required — public site."""
        return True

    async def _is_session_valid(self, page: Page) -> bool:
        """Always valid — no session to expire on a public site."""
        return True

    async def search_sku(self, page: Page, sku: str, brand: str = "") -> list[PartResult]:
        """Search for a part SKU on GoParts and extract results.

        Uses JS evaluate for all DOM access to avoid Playwright timeouts
        on this analytics-heavy site.
        """
        url = f"{SEARCH_URL}/{sku}"
        logger.info("Searching GoParts", sku=sku, url=url)

        if await self._preflight_cloudflare_challenge(url):
            return []

        response = await self._goto_search_page(page, url, sku)
        if self._last_http_block:
            return []
        if response and response.status in settings.anti_bot_block_status_codes:
            self._last_http_block = {"status": response.status, "url": url}
            return []

        await self._human_settle(page)
        if await self._detect_blocked(page):
            logger.warning("GoParts: blocked during direct SKU search", sku=sku)
            return []

        # Extract all data via a single JS evaluate call
        # This avoids multiple Playwright round-trips that can timeout
        try:
            data = await asyncio.wait_for(page.evaluate("""(searchedSku) => {
                const results = [];
                const clean = (value) => String(value || '').replace(/[\\s\\-.\\/]/g, '').toUpperCase();
                const searchedClean = clean(searchedSku);

                // Strategy 1: Product cards with prices
                const cards = document.querySelectorAll(
                    '.product-card, [class*="product"], [class*="card-product"], ' +
                    '[class*="resultado"], article, [class*="item-busca"]'
                );

                for (const card of cards) {
                    const text = card.textContent || '';

                    // Extract price
                    const priceMatch = text.match(/R\\$\\s*([\\d.,]+)/);
                    if (!priceMatch || !clean(text).includes(searchedClean)) continue;

                    const price = priceMatch[1];

                    // Extract title
                    const titleEl = card.querySelector(
                        'h2, h3, h4, .product-name, .title, ' +
                        '[class*="title"], [class*="name"], [class*="descricao"]'
                    );
                    const title = titleEl
                        ? titleEl.textContent.trim()
                        : text.split('\\n')[0].trim().substring(0, 200);

                    // Extract link
                    const linkEl = card.querySelector('a[href]');
                    const href = linkEl ? linkEl.getAttribute('href') || '' : '';

                    // Extract SKU from title or card text
                    const skuMatch = text.match(/\\b([A-Z0-9]{5,20})\\b/i);
                    const foundSku = clean(text).includes(searchedClean)
                        ? searchedSku
                        : (skuMatch ? skuMatch[1].toUpperCase() : '');

                    // Extract seller/store
                    const sellerEl = card.querySelector(
                        '[class*="seller"], [class*="loja"], ' +
                        '[class*="vendor"], [class*="concessionaria"]'
                    );
                    const seller = sellerEl ? sellerEl.textContent.trim() : '';

                    // Extract availability
                    const availEl = card.querySelector(
                        '[class*="estoque"], [class*="disponib"], ' +
                        '[class*="entrega"], [class*="frete"]'
                    );
                    const availability = availEl ? availEl.textContent.trim() : '';

                    results.push({
                        sku: foundSku,
                        price: price,
                        title: title.substring(0, 200),
                        url: href,
                        seller: seller.substring(0, 100),
                        availability: availability.substring(0, 100),
                    });

                    if (results.length >= 20) break;
                }

                // Strategy 2: Table rows from the list-of-parts layout.
                if (results.length === 0) {
                    const tables = document.querySelectorAll('.list-of-parts table, table');
                    for (const table of tables) {
                        const rows = table.querySelectorAll('tbody tr, tr');
                        for (const row of rows) {
                            const cells = row.querySelectorAll('td');
                            if (cells.length < 2) continue;

                            const cellTexts = [];
                            for (const cell of cells) {
                                cellTexts.push(cell.textContent.trim());
                            }

                            const fullText = cellTexts.join(' ');
                            if (!clean(fullText).includes(searchedClean)) continue;
                            const priceMatch = fullText.match(/R\\$\\s*([\\d.,]+)/) ||
                                               fullText.match(/(\\d{1,3}(?:\\.\\d{3})*,\\d{2})/);
                            if (!priceMatch) continue;

                            const skuMatch = fullText.match(/\\b([A-Z0-9]{5,20})\\b/i);

                            results.push({
                                sku: clean(fullText).includes(searchedClean)
                                    ? searchedSku
                                    : (skuMatch ? skuMatch[1].toUpperCase() : ''),
                                price: priceMatch[1],
                                title: cellTexts[0].substring(0, 200),
                                url: '',
                                seller: '',
                                availability: '',
                            });

                            if (results.length >= 20) break;
                        }
                        if (results.length > 0) break;
                    }
                }

                // Strategy 3: Links with product URLs
                if (results.length === 0) {
                    const links = document.querySelectorAll(
                        'a[href*="/peca/"], a[href*="/produto/"]'
                    );
                    for (const link of links) {
                        const text = link.textContent.trim();
                        const href = link.getAttribute('href') || '';

                        // Look for price in parent context
                        const parent = link.closest('div, li, article, section');
                        const parentText = parent ? parent.textContent : text;
                        const combinedText = `${text} ${parentText} ${href}`;
                        if (!clean(combinedText).includes(searchedClean)) continue;
                        const priceMatch = parentText.match(/R\\$\\s*([\\d.,]+)/);

                        const skuMatch = href.match(
                            /\\/(?:peca|produto)\\/([A-Za-z0-9-]+)/
                        );

                        results.push({
                            sku: clean(combinedText).includes(searchedClean)
                                ? searchedSku
                                : (skuMatch ? skuMatch[1].toUpperCase() : ''),
                            price: priceMatch ? priceMatch[1] : '',
                            title: text.substring(0, 200),
                            url: href,
                            seller: '',
                            availability: '',
                        });

                        if (results.length >= 15) break;
                    }
                }

                // Check for "no results" indicators
                const bodyText = document.body ? document.body.textContent || '' : '';
                const noResults = bodyText.includes('Nenhum resultado') ||
                                  bodyText.includes('Nenhum produto') ||
                                  bodyText.includes('Não encontramos');

                return {
                    results: results,
                    noResults: noResults,
                    title: document.title,
                };
            }""", sku), timeout=15000)
        except Exception as e:
            logger.warning("GoParts: JS evaluate failed", sku=sku, error=str(e))
            return []

        if data.get("noResults"):
            logger.info("GoParts: no results found", sku=sku)
            return []

        # Convert JS results to PartResult objects
        results: list[PartResult] = []
        for item in data.get("results", []):
            price = self._parse_price(item.get("price", ""))
            found_sku = item.get("sku", "")
            href = item.get("url", "")

            # Build product URL
            product_url = ""
            if href:
                if href.startswith("/"):
                    product_url = f"{BASE_URL}{href}"
                elif href.startswith("http"):
                    product_url = href
                else:
                    product_url = f"{BASE_URL}/{href}"

            exact = (
                self.validate_exact_match(sku, found_sku) if found_sku else False
            )

            results.append(
                PartResult(
                    sku_searched=sku,
                    sku_found=found_sku or sku,
                    exact_match=exact,
                    site=self.site_id,
                    site_name=self.site_name,
                    price=price,
                    currency=Currency.BRL,
                    condition=ItemCondition.UNKNOWN,
                    availability=item.get("availability", "unknown") or "unknown",
                    seller_name=item.get("seller", ""),
                    product_url=product_url or str(page.url),
                    origin="Brasil",
                    raw_title=item.get("title", ""),
                )
            )

        logger.info("GoParts: extracted results", sku=sku, count=len(results))
        return results

    async def _preflight_cloudflare_challenge(self, url: str) -> bool:
        """Avoid headless Chromium hangs when Cloudflare already exposes a challenge."""
        if not settings.playwright_headless:
            return False

        headers = {
            "User-Agent": self._select_user_agent(),
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;q=0.9,"
                "image/avif,image/webp,image/apng,*/*;q=0.8"
            ),
            "Accept-Language": settings.browser_accept_language,
        }
        try:
            async with httpx.AsyncClient(
                follow_redirects=True,
                timeout=httpx.Timeout(8.0),
                headers=headers,
            ) as client:
                response = await client.get(url)
        except Exception as e:
            logger.debug("GoParts: preflight skipped after HTTP error", error=str(e))
            return False

        if (
            response.headers.get("cf-mitigated", "").lower() == "challenge"
            or (
                response.status_code in settings.anti_bot_block_status_codes
                and response.headers.get("server", "").lower() == "cloudflare"
            )
        ):
            self._last_http_block = {"status": response.status_code, "url": str(response.url)}
            logger.warning(
                "GoParts: Cloudflare challenge detected before browser navigation",
                status=response.status_code,
                url=str(response.url),
            )
            return True

        return False

    async def _goto_search_page(self, page: Page, url: str, sku: str):
        """Navigate with a hard watchdog for Cloudflare challenge renderer hangs."""
        nav_task = asyncio.create_task(page.goto(url, wait_until="commit", timeout=10000))
        _done, pending = await asyncio.wait({nav_task}, timeout=14)
        if pending:
            self._last_http_block = {"status": "navigation_timeout", "url": url}
            logger.warning("GoParts: navigation watchdog timed out", sku=sku, url=url)
            with contextlib.suppress(Exception):
                await page.close()
            with contextlib.suppress(Exception):
                await asyncio.wait_for(nav_task, timeout=2)
            return None

        try:
            return nav_task.result()
        except (TimeoutError, PlaywrightTimeoutError):
            logger.warning("GoParts: direct URL navigation timed out", sku=sku, url=url)
            with contextlib.suppress(Exception):
                await asyncio.wait_for(page.evaluate("window.stop()"), timeout=3000)
        except Exception as e:
            logger.warning("GoParts: direct URL navigation failed", sku=sku, url=url, error=str(e))
        return None

    async def _human_settle(self, page: Page) -> None:
        """Let the direct search page render with human-paced movement."""
        await self._action_delay(1800, 3600)
        try:
            viewport = page.viewport_size or {"width": 1366, "height": 768}
            await page.mouse.move(
                random.randint(120, max(121, viewport["width"] - 120)),
                random.randint(120, max(121, viewport["height"] - 120)),
                steps=random.randint(8, 18),
            )
            await self._action_delay(600, 1300)
            await page.mouse.wheel(0, random.randint(280, 760))
            await self._action_delay(1800, 3200)
            await page.mouse.wheel(0, -random.randint(80, 260))
            await self._action_delay(800, 1600)
        except Exception as e:
            logger.debug("GoParts: human settle interaction skipped", error=str(e))

    @staticmethod
    def _parse_price(price_text: str) -> float | None:
        return BaseScraper.parse_brazilian_price(price_text)
