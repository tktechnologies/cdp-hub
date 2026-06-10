"""VW Official scraper — pecas.vw.com.br.

Site characteristics:
- Platform: VTEX/SPA-based VW official parts store
- Search: /todas-categorias?q={SKU}
- No login required
- CEP must be checked/updated for dealer price visibility
- Results are dynamic/client-side rendered
- Only sells genuine, mostly new parts

Key business rules:
- VW SKUs must have spaces/slashes/dots removed (e.g., 5C0941005K)
- Sometimes suffix indicates color/finish
- If item is not available, site might say "Produto amplamente esgotado"
"""

import re

import structlog
from playwright.async_api import Page

from src.models.schemas import Currency, ItemCondition, PartResult, SiteId
from src.scrapers.base import BaseScraper

logger = structlog.get_logger()

BASE_URL = "https://pecas.vw.com.br"
CEP = "80220001"


class VWScraper(BaseScraper):
    """Scraper for VW Official Store (pecas.vw.com.br).

    No authentication required for basic search.

    Search flow:
        1. Check/set CEP for dealer pricing
        2. Navigate to /todas-categorias?q={SKU}
        3. Wait for SPA to render results
        4. Extract product info, prices, availability, dealer info
    """

    @property
    def site_id(self) -> SiteId:
        return SiteId.VW

    @property
    def site_name(self) -> str:
        return "VW Official"

    @property
    def base_url(self) -> str:
        return BASE_URL

    async def login(self, page: Page) -> bool:
        """Set CEP for dealer pricing on first visit."""
        try:
            logger.info("VW: checking/setting CEP", cep=CEP)
            await page.goto(self.base_url, wait_until="domcontentloaded", timeout=30000)
            await self._wait_for_page_settle()

            if await self._check_and_update_cep(page):
                return True

            logger.info("VW: CEP check completed, continuing")
            return True

        except Exception as e:
            logger.error("VW: CEP setup failed", error=str(e))
            return True  # Continue anyway — search may still work

    async def _check_and_update_cep(self, page: Page) -> bool:
        """Check if our CEP is set; if not, update it."""
        # Check if CEP is already displayed on the page
        body_text = await page.inner_text("body")
        formatted_cep = f"{CEP[:5]}-{CEP[5:]}"

        if formatted_cep in body_text or CEP in body_text:
            logger.info("VW: CEP already set", cep=CEP)
            return True

        # Look for CEP input field
        cep_selectors = [
            'input[placeholder*="CEP"]',
            'input[name*="cep"]',
            'input[id*="cep"]',
            'input[class*="cep"]',
            'input[placeholder*="Informe"]',
        ]
        for selector in cep_selectors:
            cep_input = page.locator(selector).first
            if await cep_input.is_visible():
                await cep_input.click()
                await self._wait_for_micro_interaction()
                await cep_input.fill("")
                await cep_input.fill(CEP)
                await self._wait_for_micro_interaction()
                logger.info("VW: CEP filled", cep=CEP)

                # Submit
                confirm_btn = (
                    page.locator("button")
                    .filter(
                        has_text=re.compile(
                            r"OK|Confirmar|Atualizar|Buscar|Aplicar|Localizar", re.I
                        )
                    )
                    .first
                )
                if await confirm_btn.is_visible():
                    await confirm_btn.click()
                else:
                    await page.keyboard.press("Enter")

                await self._wait_for_post_submit()
                logger.info("VW: CEP submitted")
                return True

        # Try clicking a CEP trigger element
        cep_trigger = (
            page.locator("button, a, div, span")
            .filter(has_text=re.compile(r"CEP|Informe|Localização|01001-000", re.I))
            .first
        )
        if await cep_trigger.is_visible():
            await cep_trigger.click()
            await self._wait_for_page_settle()

            # After clicking, look for newly visible CEP input
            for selector in cep_selectors:
                cep_input = page.locator(selector).first
                if await cep_input.is_visible():
                    await cep_input.click()
                    await cep_input.fill("")
                    await cep_input.fill(CEP)
                    await page.keyboard.press("Enter")
                    await self._wait_for_post_submit()
                    logger.info("VW: CEP updated via dialog", cep=CEP)
                    return True

        logger.info("VW: no CEP input found, continuing")
        return False

    async def _is_session_valid(self, page: Page) -> bool:
        """Check if CEP is already set in this session."""
        try:
            await page.goto(self.base_url, wait_until="domcontentloaded", timeout=30000)
            await self._wait_for_page_settle()
            body_text = await page.inner_text("body")
            formatted_cep = f"{CEP[:5]}-{CEP[5:]}"
            return formatted_cep in body_text or CEP in body_text
        except Exception:
            return True  # Don't block on session check failures

    def _normalize_sku(self, sku: str, brand: str = "") -> str:
        """Apply VW-specific SKU normalization rules.
        Removes all spaces, dashes, dots, and slashes.
        """
        return re.sub(r"[\s\.\-/]", "", sku).upper()

    async def search_sku(self, page: Page, sku: str, brand: str = "") -> list[PartResult]:
        """Search for a part on VW official site.

        Uses /todas-categorias?q={SKU}
        """
        url = f"{BASE_URL}/todas-categorias?q={sku}"
        logger.info("Searching VW Official", sku=sku, url=url)

        await page.goto(url, wait_until="domcontentloaded", timeout=20000)
        await self._wait_for_results(
            page,
            '[class*="product"], [class*="card"], [class*="item"], article, div.shelf-item',
        )

        # Check for blocked page
        if await self._detect_blocked(page):
            logger.warning("VW: blocked during search", sku=sku)
            return []

        data = await page.evaluate(
            """(searchedSku) => {
            const results = [];

            // Find product cards
            const cards = document.querySelectorAll(
                '[class*="productCard"], [class*="product-card"], [class*="shelf-item"], ' +
                '[class*="gallery-item"], [class*="vtex-search-result"], ' +
                '[class*="product-summary"], article, li[class*="product"]'
            );

            for (const card of cards) {
                const text = card.textContent || '';

                // Need price
                const allPrices = [...text.matchAll(/R\\$\\s*([\\d.,]+)/g)];
                if (allPrices.length === 0) continue;

                // Collect all prices
                const prices = allPrices.map(m => m[1]);
                let listPrice = prices[0];
                let pixPrice = '';

                // Look for PIX/best price label
                const pixMatch = text.match(/(?:PIX|[àÀ]\\s*vista|desconto)[\\s:]*R\\$\\s*([\\d.,]+)/i);
                if (pixMatch) {
                    pixPrice = pixMatch[1];
                } else if (prices.length > 1) {
                    pixPrice = prices[prices.length - 1];
                }

                // Title
                const titleEl = card.querySelector(
                    'h1, h2, h3, [class*="productName"], [class*="title"], [class*="name"]'
                );
                const title = titleEl
                    ? titleEl.textContent.trim()
                    : text.split('\\n').filter(l => l.trim().length > 5)[0]?.trim() || '';

                // Link
                const linkEl = card.querySelector('a[href*="/p"], a[href*="/produto"]');
                const href = linkEl ? linkEl.getAttribute('href') || '' : '';

                // Extract a part number if visible in title
                let foundSku = '';
                const refMatch = title.match(new RegExp(searchedSku.replace(/[-\\.]/g, ''), 'i'));
                if (refMatch) {
                    foundSku = searchedSku;
                } else {
                    const skuMatch = title.match(/\\b([A-Z0-9]{5,15})\\b/);
                    if (skuMatch) foundSku = skuMatch[1];
                }

                // Seller/dealer info
                const sellerEl = card.querySelector(
                    '[class*="seller"], [class*="dealer"], [class*="concession"], ' +
                    '[class*="loja"], [class*="vendor"]'
                );
                const seller = sellerEl ? sellerEl.textContent.trim() : 'VW Concessionárias';

                // Availability
                const availEl = card.querySelector(
                    '[class*="stock"], [class*="disponib"], button[class*="buy"], ' +
                    '[class*="availability"]'
                );
                let availability = 'unknown';
                if (availEl) {
                    availability = availEl.textContent.trim();
                }
                if (text.toLowerCase().includes('esgotado') || text.toLowerCase().includes('indisponível')) {
                    availability = 'Esgotado';
                } else if (text.toLowerCase().includes('disponível') || text.toLowerCase().includes('comprar')) {
                    availability = 'Disponível';
                }

                results.push({
                    title: title ? title.substring(0, 300) : '',
                    listPrice: listPrice,
                    pixPrice: pixPrice,
                    allPrices: prices,
                    url: href,
                    sku: foundSku,
                    seller: seller.substring(0, 200),
                    availability: availability.substring(0, 100),
                });

                if (results.length >= 10) break;
            }

            // Backup strategy: product URLs with prices
            if (results.length === 0) {
                const links = document.querySelectorAll('a[href*="/p"], a[href*="/produto"]');
                for (const link of links) {
                    const parent = link.parentElement?.parentElement;
                    if (!parent) continue;

                    const text = parent.textContent || '';
                    const allPrices = [...text.matchAll(/R\\$\\s*([\\d.,]+)/g)];
                    if (allPrices.length === 0) continue;

                    results.push({
                        title: link.textContent.trim().substring(0, 300),
                        listPrice: allPrices[0][1],
                        pixPrice: allPrices.length > 1 ? allPrices[allPrices.length - 1][1] : '',
                        allPrices: allPrices.map(m => m[1]),
                        url: link.getAttribute('href') || '',
                        sku: '',
                        seller: 'VW Concessionárias',
                        availability: 'unknown',
                    });

                    if (results.length >= 10) break;
                }
            }

            const bodyText = document.body ? document.body.textContent || '' : '';
            const noResults = bodyText.includes('não encontrados') ||
                              bodyText.includes('nenhum resultado') ||
                              bodyText.includes('não encontramos') ||
                              bodyText.includes('nenhum produto');

            return {
                results: results,
                noResults: noResults,
                title: document.title
            };
        }""",
            sku,
        )

        if data.get("noResults"):
            logger.info("VW Official: no results found", sku=sku)
            return []

        results: list[PartResult] = []
        for item in data.get("results", []):
            # Use PIX price if available
            pix_price = self._parse_price(item.get("pixPrice", ""))
            list_price = self._parse_price(item.get("listPrice", ""))
            final_price = pix_price or list_price

            href = item.get("url", "")
            found_sku = item.get("sku", "")

            product_url = href
            if href.startswith("/"):
                product_url = f"{BASE_URL}{href}"
            elif href and not href.startswith("http"):
                product_url = f"{BASE_URL}/{href}"

            exact = self.validate_exact_match(sku, found_sku) if found_sku else False
            if not exact:
                exact = self._contains_sku(item.get("title", ""), sku) or self._contains_sku(
                    product_url, sku
                )
                if exact and not found_sku:
                    found_sku = sku

            results.append(
                PartResult(
                    sku_searched=sku,
                    sku_found=found_sku or sku,
                    exact_match=exact,
                    site=self.site_id,
                    site_name=self.site_name,
                    price=final_price,
                    currency=Currency.BRL,
                    condition=ItemCondition.NEW,
                    availability=item.get("availability", "unknown"),
                    seller_name=item.get("seller", "VW Concessionárias"),
                    product_url=product_url or str(page.url),
                    origin="Brasil",
                    raw_title=item.get("title", ""),
                )
            )

        logger.info("VW Official: extracted results", sku=sku, count=len(results))
        return results

    @staticmethod
    def _parse_price(price_text: str) -> float | None:
        return BaseScraper.parse_brazilian_price(price_text)

    @staticmethod
    def _contains_sku(text: str, searched_sku: str) -> bool:
        return BaseScraper.contains_sku(text, searched_sku)
