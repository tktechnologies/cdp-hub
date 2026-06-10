"""eBay scraper — ebay.com.

Site characteristics (discovered 2026-02-20):
- Platform: eBay marketplace (global)
- Search: /sch/i.html?_nkw={SKU}&_sacat=6028 (auto parts category)
- No login required for search
- Anti-bot blocks raw HTTP requests but Playwright headless passes
- eBay obfuscates DOM class names frequently — s-item may not always be present
- Uses a mix of server-rendered and client-rendered content
- Prices in USD/BRL depending on locale

Used for international price comparison (especially US parts).

Key business rules:
- Prices typically in USD, may show BRL for Brazilian users
- Condition clearly labeled (New, Used, etc.)
- Multiple sellers on marketplace
- Auto parts category ID: 6028
"""

import contextlib
import re

import structlog
from playwright.async_api import Page

from src.models.schemas import Currency, ItemCondition, PartResult, SiteId
from src.scrapers.base import BaseScraper

logger = structlog.get_logger()

BASE_URL = "https://www.ebay.com"
SEARCH_URL = f"{BASE_URL}/sch/i.html"
AUTO_PARTS_CATEGORY = "6028"


class EbayScraper(BaseScraper):
    """Scraper for eBay — global automotive parts marketplace.

    No authentication required. Works in headless mode.

    eBay frequently changes its DOM class names as an anti-scraping measure.
    This scraper uses multiple fallback strategies:
    1. Standard eBay classes (.s-item, .s-item__title, etc.)
    2. List items within srp-results container
    3. Data-attribute-based selectors
    4. Text/link-based extraction as last resort

    Search flow:
        1. Navigate to /sch/i.html?_nkw={SKU}&_sacat=6028
        2. Wait for results container
        3. Extract items via JS with multiple fallback strategies
    """

    @property
    def site_id(self) -> SiteId:
        return SiteId.EBAY

    @property
    def site_name(self) -> str:
        return "eBay"

    @property
    def base_url(self) -> str:
        return BASE_URL

    async def login(self, page: Page) -> bool:
        """No authentication required for search."""
        return True

    async def _is_session_valid(self, page: Page) -> bool:
        """Always valid."""
        return True

    async def _detect_blocked(self, page: Page) -> bool:
        """Detect real eBay interstitials without flagging hidden challenge markup."""
        try:
            body_text = (await page.inner_text("body")).lower()
        except Exception:
            body_text = ""

        result_count = 0
        with contextlib.suppress(Exception):
            result_count = await page.locator(
                ".srp-results li, #srp-river-results li, [data-viewport]"
            ).count()

        body_block_indicators = [
            "access denied",
            "pardon our interruption",
            "please verify yourself",
            "please verify you are a human",
            "verify you are human",
            "checking your browser",
            "too many requests",
            "captcha",
        ]
        if result_count == 0 and any(indicator in body_text for indicator in body_block_indicators):
            logger.warning("eBay block indicator detected", site=self.site_id.value)
            return True

        challenge_locator = page.locator(
            "#challenge-running, #challenge-form, "
            "iframe[src*='captcha'], iframe[src*='challenge'], "
            "iframe[src*='turnstile'], input[name='cf-turnstile-response'], "
            "div.cf-browser-verification, div[class*='captcha']"
        )
        with contextlib.suppress(Exception):
            for index in range(min(await challenge_locator.count(), 5)):
                if await challenge_locator.nth(index).is_visible(timeout=500):
                    logger.warning("Visible eBay challenge detected", site=self.site_id.value)
                    return True

        return False

    async def search_sku(self, page: Page, sku: str, brand: str = "") -> list[PartResult]:
        """Search for a part SKU on eBay."""
        url = f"{SEARCH_URL}?_nkw={sku}&_sacat={AUTO_PARTS_CATEGORY}"
        logger.info("Searching eBay", sku=sku, url=url)

        await page.goto(url, wait_until="domcontentloaded", timeout=20000)
        await self._action_delay()

        # Wait for results container
        with contextlib.suppress(Exception):
            await page.wait_for_selector(
                ".srp-results, #srp-river-results, [class*=srp]",
                timeout=8000,
            )

        await self._wait_for_page_settle()

        # Multi-strategy extraction via JS
        try:
            data = await page.evaluate(
                """(searchedSku) => {
                const results = [];

                // Helper: extract price from text
                function extractPrice(text) {
                    const match = text.match(/(?:R\\$|US\\s*\\$|\\$|EUR|€)\\s*([\\d.,]+)/);
                    return match ? match[0] : '';
                }

                // Helper: extract condition from text
                function extractCondition(text) {
                    const lower = text.toLowerCase();
                    if (lower.includes('brand new') || lower.includes('novo') || lower.includes('new')) return 'new';
                    if (lower.includes('used') || lower.includes('usado') || lower.includes('pre-owned')) return 'used';
                    return 'unknown';
                }

                // Only real listing cards — avoid footer/nav li elements that caused tab churn.
                let items = document.querySelectorAll('li.s-item, div.s-item');

                if (items.length === 0) {
                    items = document.querySelectorAll('.srp-results li.s-card, .srp-river-results li.s-card');
                }

                if (items.length === 0) {
                    items = document.querySelectorAll('[data-viewport][data-listing-id]');
                }

                for (const item of items) {
                    const text = item.textContent || '';
                    if (text.length < 20) continue;  // Skip tiny elements

                    // Must have a price or a product link
                    const price = extractPrice(text);
                    const links = item.querySelectorAll('a[href*="itm/"], a[href*="/itm/"]');
                    if (!price && links.length === 0) continue;

                    // Title: first meaningful link text or heading
                    let title = '';
                    const headings = item.querySelectorAll('h3, h4, [role="heading"]');
                    if (headings.length > 0) {
                        title = headings[0].textContent.trim();
                    } else if (links.length > 0) {
                        for (const link of links) {
                            const linkText = link.textContent.trim();
                            if (linkText.length > 10 && linkText.length < 200) {
                                title = linkText;
                                break;
                            }
                        }
                    }
                    if (!title) continue;

                    // Skip "Shop on eBay" promotional items
                    if (title === 'Shop on eBay' || title === 'Compre no eBay') continue;

                    // URL
                    let url = '';
                    for (const link of links) {
                        const href = link.getAttribute('href') || '';
                        if (href.includes('/itm/')) {
                            url = href;
                            break;
                        }
                    }

                    // Condition
                    const condition = extractCondition(text);

                    // Location
                    const locMatch = text.match(/(?:de|from)\\s+([A-Za-zÀ-ÿ\\s,]+(?:Brazil|Brasil|China|US|USA|United States|Germany))/i);
                    const location = locMatch ? locMatch[1].trim() : '';

                    results.push({
                        title: title.substring(0, 200),
                        price: price,
                        url: url,
                        condition: condition,
                        location: location.substring(0, 60),
                    });

                    if (results.length >= 10) break;
                }

                const h1 = document.querySelector('h1');
                const resultCount = h1 ? h1.textContent.trim() : '';

                const bodyText = document.body ? document.body.textContent || '' : '';
                const noResults = bodyText.includes('No exact matches') ||
                                  bodyText.includes('Nenhum resultado') ||
                                  bodyText.includes('0 results') ||
                                  bodyText.includes('0 resultados');

                return {
                    results,
                    noResults,
                    resultCount,
                    title: document.title,
                    strategies: {
                        sItem: document.querySelectorAll('.s-item').length,
                        sCard: document.querySelectorAll('.srp-results li.s-card').length,
                        dataViewport: document.querySelectorAll('[data-viewport][data-listing-id]').length,
                    },
                };
            }""",
                sku,
            )
        except Exception as e:
            logger.warning("eBay: JS evaluate failed", sku=sku, error=str(e))
            return []

        logger.debug(
            "eBay: extraction strategies",
            strategies=data.get("strategies"),
            result_count=data.get("resultCount"),
        )

        if data.get("noResults"):
            logger.info("eBay: no results found", sku=sku)
            return []

        # Convert JS results to PartResult objects
        results: list[PartResult] = []
        for item in data.get("results", []):
            price, currency = self._parse_ebay_price(item.get("price", ""))
            title = item.get("title", "")
            found_sku = self._extract_sku_from_title(title, sku)
            condition = self._map_condition(item.get("condition", ""))

            # Clean URL
            product_url = item.get("url", "")
            if "?" in product_url:
                product_url = product_url.split("?")[0]

            exact = self.validate_exact_match(sku, found_sku) if found_sku else False

            results.append(
                PartResult(
                    sku_searched=sku,
                    sku_found=found_sku or sku,
                    exact_match=exact,
                    site=self.site_id,
                    site_name=self.site_name,
                    price=price,
                    currency=currency,
                    condition=condition,
                    availability="in_stock",
                    seller_name="",
                    product_url=product_url or str(page.url),
                    origin=item.get("location", ""),
                    raw_title=title,
                )
            )

        logger.info("eBay: extracted results", sku=sku, count=len(results))
        return results

    @staticmethod
    def _parse_ebay_price(price_text: str) -> tuple[float | None, Currency]:
        """Parse eBay price format. Handles USD, BRL, EUR."""
        if not price_text:
            return None, Currency.USD

        currency = Currency.USD
        if "R$" in price_text:
            currency = Currency.BRL
        elif "EUR" in price_text or "€" in price_text:
            currency = Currency.EUR

        # Handle range prices — take first
        if " to " in price_text or " a " in price_text:
            price_text = re.split(r"\s+(?:to|a)\s+", price_text)[0]

        match = re.search(r"[\d.,]+", price_text)
        if match:
            return EbayScraper._parse_price_number(match.group()), currency

        return None, currency

    @staticmethod
    def _parse_price_number(raw_number: str) -> float | None:
        """Parse marketplace prices with Brazilian, European, or US separators."""
        cleaned = re.sub(r"[^\d.,]", "", raw_number)
        if not cleaned:
            return None

        if "." in cleaned and "," in cleaned:
            if cleaned.rfind(".") > cleaned.rfind(","):
                cleaned = cleaned.replace(",", "")
            else:
                cleaned = cleaned.replace(".", "").replace(",", ".")
        elif "," in cleaned:
            cleaned = cleaned.replace(".", "").replace(",", ".")
        elif "." in cleaned:
            decimal_digits = len(cleaned.rsplit(".", maxsplit=1)[-1])
            if decimal_digits != 2:
                cleaned = cleaned.replace(".", "")

        try:
            value = float(cleaned)
        except ValueError:
            return None
        return value if value > 0 else None

    @staticmethod
    def _extract_sku_from_title(title: str, searched_sku: str) -> str:
        """Extract part number from eBay listing title."""
        if searched_sku.upper() in title.upper():
            return searched_sku.upper()
        match = re.search(r"\b([A-Z0-9]{5,20})\b", title)
        return match.group(1) if match else ""

    @staticmethod
    def _map_condition(cond_text: str) -> ItemCondition:
        """Map eBay condition text to ItemCondition."""
        lower = cond_text.lower()
        if "new" in lower or "novo" in lower:
            return ItemCondition.NEW
        if "used" in lower or "usado" in lower:
            return ItemCondition.USED
        return ItemCondition.UNKNOWN
