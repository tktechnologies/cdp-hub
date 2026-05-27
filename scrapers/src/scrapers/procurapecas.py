"""Procura Peças scraper — procurapecas.com.br.

Site characteristics:
- Platform: VTEX Commerce (Brazilian e-commerce platform)
- Search: URL-based — /{SKU} (direct path)
- No login required (public e-commerce)
- No CEP required
- Results: VTEX product cards with prices, SKU in title as REF:.{SKU}
- Product URLs: /slug/p

Key business rules:
- Price in BRL (R$ format), has both list price and PIX discount
- Product names contain REF:.{SKU} pattern for part number identification
- Single seller store — Procura Peças is the seller
- Must extract ALL prices visible on the page (list, PIX, promotional)
"""

import structlog
from playwright.async_api import Page

from src.models.schemas import Currency, ItemCondition, PartResult, SiteId
from src.scrapers.base import BaseScraper

logger = structlog.get_logger()

BASE_URL = "https://procurapecas.com.br"


class ProcuraPecasScraper(BaseScraper):
    """Scraper for Procura Peças — VTEX-based automotive parts store.

    This is a public e-commerce site (not an aggregator). No auth required.

    Search flow:
        1. Navigate to /{SKU} (direct path search)
        2. Wait for product gallery to load
        3. Extract all product cards with ALL prices
        4. Capture seller/shop info where available
    """

    @property
    def site_id(self) -> SiteId:
        return SiteId.PROCURA_PECAS

    @property
    def site_name(self) -> str:
        return "Procura Peças"

    @property
    def base_url(self) -> str:
        return BASE_URL

    async def login(self, page: Page) -> bool:
        """No authentication required — public e-commerce site."""
        return True

    async def _is_session_valid(self, page: Page) -> bool:
        """Always valid — no session to expire on a public site."""
        return True

    async def search_sku(self, page: Page, sku: str, brand: str = "") -> list[PartResult]:
        """Search for a part SKU on Procura Peças.

        Uses direct path URL: /{SKU}
        """
        url = f"{BASE_URL}/{sku}"
        logger.info("Searching Procura Peças", sku=sku, url=url)

        await page.goto(url, wait_until="domcontentloaded", timeout=20000)
        await self._wait_for_page_settle()

        # Check for blocked page
        if await self._detect_blocked(page):
            logger.warning("ProcuraPeças: blocked during search", sku=sku)
            return []

        # Check for no results
        body_text = await page.inner_text("body")
        lower_text = body_text.lower()
        if any(phrase in lower_text for phrase in [
            "nenhum resultado", "não encontramos", "nenhum produto",
            "página não encontrada", "404",
        ]):
            logger.info("Procura Peças: no results found", sku=sku)
            return []

        # Extract all data via JS evaluate
        try:
            data = await page.evaluate(
                """(searchedSku) => {
                const results = [];

                // Strategy 1: VTEX product cards (shelf items)
                const cards = document.querySelectorAll(
                    '[class*="productCard"], [class*="product-card"], ' +
                    '[class*="shelf-item"], [class*="product-summary"], ' +
                    '[class*="gallery-item"], [class*="vtex-search-result"], ' +
                    'article[class*="product"], [class*="searchResult"], ' +
                    '[class*="product-item"], li[class*="product"]'
                );

                for (const card of cards) {
                    const text = card.textContent || '';

                    // Extract ALL prices — collect every R$ pattern
                    const allPrices = [...text.matchAll(/R\\$\\s*([\\d.,]+)/g)];
                    if (allPrices.length === 0) continue;

                    // Parse all price values
                    const prices = allPrices.map(m => m[1]);

                    // Identify specific price types
                    let listPrice = prices[0];
                    let pixPrice = '';
                    let bestPrice = prices[0];

                    // Look for PIX/promotional price labels
                    const pixMatch = text.match(/(?:PIX|[àÀ]\\s*vista|desconto)[\\s:]*R\\$\\s*([\\d.,]+)/i);
                    if (pixMatch) {
                        pixPrice = pixMatch[1];
                    } else if (prices.length > 1) {
                        // Last price is often the PIX/best price
                        pixPrice = prices[prices.length - 1];
                    }

                    // Extract title
                    const titleEl = card.querySelector(
                        'h1, h2, h3, [class*="productName"], [class*="product-name"], ' +
                        '[class*="productBrand"], a[class*="clearLink"]'
                    );
                    const title = titleEl
                        ? titleEl.textContent.trim()
                        : text.split('\\n').filter(l => l.trim().length > 5)[0]?.trim()?.substring(0, 200) || '';

                    // Extract product link
                    const linkEl = card.querySelector('a[href*="/p"]');
                    const href = linkEl ? linkEl.getAttribute('href') || '' : '';

                    // Extract SKU from title (REF:.XXXXX pattern)
                    const refMatch = title.match(/REF[.:]*\\s*([A-Za-z0-9.\\-]+)/i);
                    const foundSku = refMatch ? refMatch[1].replace(/^[.]/, '') : '';

                    // Extract seller info if available
                    const sellerEl = card.querySelector(
                        '[class*="seller"], [class*="vendor"], [class*="loja"]'
                    );
                    const seller = sellerEl ? sellerEl.textContent.trim() : 'Procura Peças';

                    // Extract availability
                    const availEl = card.querySelector(
                        '[class*="stock"], [class*="disponib"], button[class*="buy"]'
                    );
                    const availability = availEl ? availEl.textContent.trim() : 'unknown';

                    results.push({
                        sku: foundSku,
                        listPrice: listPrice,
                        pixPrice: pixPrice,
                        bestPrice: bestPrice,
                        allPrices: prices,
                        title: title.substring(0, 300),
                        url: href,
                        seller: seller.substring(0, 200),
                        availability: availability.substring(0, 100),
                    });

                    if (results.length >= 20) break;
                }

                // Strategy 2: If no VTEX cards, try generic product elements
                if (results.length === 0) {
                    const links = document.querySelectorAll('a[href$="/p"]');
                    for (const link of links) {
                        const parent = link.closest('div, li, section, article') || link;
                        const text = parent.textContent || '';
                        const allPrices = [...text.matchAll(/R\\$\\s*([\\d.,]+)/g)];

                        const title = link.textContent.trim();
                        const href = link.getAttribute('href') || '';
                        const refMatch = title.match(/REF[.:]*\\s*([A-Za-z0-9.\\-]+)/i);

                        results.push({
                            sku: refMatch ? refMatch[1].replace(/^[.]/, '') : '',
                            listPrice: allPrices.length > 0 ? allPrices[0][1] : '',
                            pixPrice: allPrices.length > 1 ? allPrices[allPrices.length - 1][1] : '',
                            bestPrice: allPrices.length > 0 ? allPrices[0][1] : '',
                            allPrices: allPrices.map(m => m[1]),
                            title: title.substring(0, 300),
                            url: href,
                            seller: 'Procura Peças',
                            availability: 'unknown',
                        });

                        if (results.length >= 20) break;
                    }
                }

                return { results: results };
            }""",
                sku,
            )
        except Exception as e:
            logger.warning("Procura Peças: JS evaluate failed", sku=sku, error=str(e))
            return []

        # Convert JS results to PartResult objects
        results: list[PartResult] = []
        for item in data.get("results", []):
            # Use PIX price if available (best price for customer), otherwise list price
            pix_price = self._parse_price(item.get("pixPrice", ""))
            list_price = self._parse_price(item.get("listPrice", ""))
            final_price = pix_price or list_price

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
                    price=final_price,
                    currency=Currency.BRL,
                    condition=ItemCondition.NEW,  # Procura Peças sells new parts
                    availability=item.get("availability", "unknown"),
                    seller_name=item.get("seller", "Procura Peças"),
                    product_url=product_url or str(page.url),
                    origin="Brasil",
                    raw_title=item.get("title", ""),
                )
            )

        logger.info("Procura Peças: extracted results", sku=sku, count=len(results))
        return results

    @staticmethod
    def _parse_price(price_text: str) -> float | None:
        return BaseScraper.parse_brazilian_price(price_text)
