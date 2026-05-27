"""EU Imports scraper — export.fastparts.is.

Site characteristics (discovered 2026-02-20):
- Platform: Angular SPA (PrimeNG)
- Domain: export.fastparts.is
- Search: Uses an input with placeholder "Enter part code..." and Enter key.
- Requires Playwright waiting for network idle / elements.
- Table format: Manufacturer, Part Number, Delivery, Price, Quantity.
- Prices in USD or EUR depending on locale.
- Availability is often "3-6 weeks, warehouse #1".

Key business rules:
- Imports typically have a 2.5x markup + shipping + exchange rate formula.
  (This scraper returns the raw foreign price/currency; higher logic handles markup).
- Only new/original parts.
- Ships from Europe/Germany.
"""

import re

import structlog
from playwright.async_api import Page

from src.models.schemas import Currency, ItemCondition, PartResult, SiteId
from src.scrapers.base import BaseScraper

logger = structlog.get_logger()

BASE_URL = "https://export.fastparts.is"


class EUImportsScraper(BaseScraper):
    """Scraper for EU Imports (export.fastparts.is).

    This site is an Angular SPA. It requires filling the search input and pressing Enter.
    """

    @property
    def site_id(self) -> SiteId:
        return SiteId.EUROPE

    @property
    def site_name(self) -> str:
        return "EU Imports"

    @property
    def base_url(self) -> str:
        return BASE_URL

    async def login(self, page: Page) -> bool:
        """No log in required."""
        return True

    async def _is_session_valid(self, page: Page) -> bool:
        """Always valid."""
        return True

    async def search_sku(self, page: Page, sku: str, brand: str = "") -> list[PartResult]:
        """Search for a part on EU Imports (fastparts.is)."""
        logger.info("Searching EU Imports", sku=sku, url=BASE_URL)

        await page.goto(BASE_URL, wait_until="domcontentloaded", timeout=30000)
        await self._action_delay()

        # Wait for the search input to appear (Angular SPA)
        input_sel = "input[placeholder*='part code']"
        try:
            await page.wait_for_selector(input_sel, timeout=10000)
        except Exception:
            logger.warning("EU Imports: Search input not found (timeout).")
            return []

        # Fill and search
        await page.fill(input_sel, sku)
        await page.press(input_sel, "Enter")

        await self._wait_for_post_submit()

        data = await page.evaluate(
            """(searchedSku) => {
            const results = [];
            
            // Check for No Parts Found message
            const bodyStr = document.body.textContent || '';
            const noResults = bodyStr.includes('No parts found') || 
                              bodyStr.includes('Not found');
                              
            if (noResults) {
                return { results: [], noResults: true };
            }

            // Look for table rows
            const rows = document.querySelectorAll('tr, .p-datatable-row');
            
            for (const row of rows) {
                const text = row.textContent || '';
                
                // Make sure it looks like a product row, not header
                if (text.includes('Manufacturer') && text.includes('Quantity')) continue;
                
                // Must have a currency symbol
                if (!text.includes('€') && !text.includes('EUR') && !text.includes('$')) continue;
                
                const cells = Array.from(row.querySelectorAll('td'))
                    .map(td => td.textContent.trim().replace(/\\s+/g, ' '));
                
                if (cells.length >= 4) {
                    // Typical columns:
                    // 0: Photo
                    // 1: Manufacturer & Part Number
                    // 2: Delivery
                    // 3: Price
                    
                    // We extract all text to be safe
                    const fullText = cells.join(' | ');
                    
                    // Price extraction
                    let priceText = '';
                    const priceMatch = fullText.match(/(?:(?:€|EUR|\\$)\\s*[\\d.,]+|[\\d.,]+\\s*(?:€|EUR|\\$))/i);
                    if (priceMatch) {
                        priceText = priceMatch[0];
                    }
                    
                    // Found SKU
                    let foundSku = '';
                    const skuMatch = fullText.match(/[A-Z0-9]{5,20}/);
                    if (skuMatch) foundSku = skuMatch[0];

                    // Brand/Manufacturer
                    let mfr = '';
                    if (fullText.includes('VAG')) mfr = 'VAG';
                    else mfr = cells[1] ? cells[1].split(' ')[0] : 'Unknown';

                    results.push({
                        title: cells.slice(1, 3).join(' - '),
                        price: priceText,
                        sku: foundSku,
                        url: '', // table rows usually don't have individual product links here
                        seller: mfr,
                        delivery: cells[2] || '',
                        quantity: cells[4] || ''
                    });
                }
            }

            return {
                results: results,
                noResults: false
            };
        }""",
            sku,
        )

        if data.get("noResults"):
            logger.info("EU Imports: no results found", sku=sku)
            return []

        results: list[PartResult] = []
        for item in data.get("results", []):
            price_text = item.get("price", "")
            price, currency = self._parse_price_and_currency(price_text)
            if price is None:
                continue
            if self._parse_quantity(item.get("quantity", "")) == 0:
                continue
            found_sku = item.get("sku", "")

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
                    condition=ItemCondition.NEW,
                    availability=item.get("delivery", "in_stock"),
                    seller_name=item.get("seller", "EU Warehouse"),
                    product_url=str(page.url),
                    origin="Europa / Alemanha",
                    raw_title=item.get("title", ""),
                )
            )

        logger.info("EU Imports: extracted results", sku=sku, count=len(results))
        return results

    @staticmethod
    def _parse_quantity(quantity_text: str) -> int | None:
        if not quantity_text:
            return None
        match = re.search(r"\d+", quantity_text)
        return int(match.group()) if match else None

    @staticmethod
    def _parse_price_and_currency(price_text: str) -> tuple[float | None, Currency]:
        if not price_text:
            return None, Currency.USD

        currency = Currency.USD
        if "€" in price_text or "EUR" in price_text.upper():
            currency = Currency.EUR

        try:
            cleaned = re.sub(r"[^\d.,]", "", price_text)
            # handle formats like 890.22 vs 890,22. EU uses commas for decimals mostly, 
            # but US formatting uses periods. In the debug script, it was "890.22 $".
            if "." in cleaned and "," in cleaned:
                # 1,234.56 or 1.234,56
                if cleaned.rfind(".") > cleaned.rfind(","):
                    # 1,234.56 format
                    cleaned = cleaned.replace(",", "")
                else:
                    # 1.234,56 format
                    cleaned = cleaned.replace(".", "").replace(",", ".")
            elif "," in cleaned:
                cleaned = cleaned.replace(",", ".")
            
            value = float(cleaned)
            return value if value > 0 else None, currency
        except (ValueError, AttributeError):
            return None, currency
