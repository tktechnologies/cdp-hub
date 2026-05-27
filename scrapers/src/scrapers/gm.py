"""GM / Chevrolet Parts scraper — pecachevrolet.com.br.

- Site: https://www.pecachevrolet.com.br
- Search: /pesquisa/?nomepeca=&grupo=&nomeveiculo=&ano=&numeropeca={SKU}
- No login required (public search)
- CEP must be set to see dealer prices
- Results: product listing with dealer/shop prices in details page
- SKU format: pure numeric or alphanumeric (e.g., 84250224, 5U6867287Y20)
- Business rules: only new, original parts; prices in BRL
- Browser launch uses BaseScraper so proxy rotation and PLAYWRIGHT_HEADLESS apply
"""

import re
from typing import Any

import structlog
from playwright.async_api import Page

from src.models.schemas import Currency, ItemCondition, PartResult, SiteId
from src.scrapers.base import BaseScraper

logger = structlog.get_logger()

BASE_URL = "https://www.pecachevrolet.com.br"
CEP = "80220001"


class GMScraper(BaseScraper):
    """Scraper for the Chevrolet Parts portal (pecachevrolet.com.br).

    This is a public e-commerce site — no authentication required.

    Search flow:
        1. Set CEP to unlock dealer prices
        2. Navigate to /pesquisa/?numeropeca={SKU}
        3. Wait for product results to load
        4. Click into each product details page
        5. Extract all dealer/shop prices from the details page
        6. Return one PartResult per dealer/price combination
    """

    @property
    def site_id(self) -> SiteId:
        return SiteId.GM

    @property
    def site_name(self) -> str:
        return "Chevrolet Parts (pecachevrolet.com.br)"

    @property
    def base_url(self) -> str:
        """Override base_url — we always use the known portal URL."""
        return BASE_URL

    async def login(self, page: Page) -> bool:
        """Set the dealership location via CEP to unlock prices."""
        try:
            logger.info("GM login: Setting dealership via CEP", cep=CEP)
            await page.goto(self.base_url, wait_until="domcontentloaded", timeout=60000)
            await self._wait_for_page_settle()

            # Try to set CEP — modal may appear on first visit
            if await self._set_cep(page):
                return True

            # If modal didn't show, find the header CEP control and click it
            header_cep = page.locator(".header-items-right-cep").first
            if not await header_cep.is_visible():
                header_cep = page.locator('button, div, a').filter(
                    has_text=re.compile(r"(01001-000|Informe seu CEP|CEP)", re.I)
                ).first

            if await header_cep.is_visible():
                await header_cep.click()
                await self._wait_for_page_settle()
                if await self._set_cep(page):
                    return True

            logger.warning("GM login: CEP input not found, continuing without price unlock")
            return True

        except Exception as e:
            logger.error("GM login failed to set CEP", error=str(e))
            return False

    async def _set_cep(self, page: Page) -> bool:
        """Click the CEP field, fill it, submit, and verify the update."""
        cep_inputs = page.locator('input[placeholder*="CEP"], input.input-CEP')
        for index in range(await cep_inputs.count()):
            cep_input = cep_inputs.nth(index)
            if not await cep_input.is_visible():
                continue

            # Click the field first so the user can watch
            await cep_input.click()
            await self._wait_for_micro_interaction()

            # Clear and fill CEP
            await cep_input.fill("")
            await cep_input.fill(CEP)
            await self._wait_for_micro_interaction()
            logger.info("GM: CEP field filled", cep=CEP)

            # Submit via button or Enter
            localizar = page.locator("button").filter(
                has_text=re.compile(r"Localizar|Buscar|Confirmar|OK", re.I)
            ).first
            if await localizar.is_visible():
                await localizar.click()
                logger.info("GM: CEP submit button clicked")
            else:
                await page.keyboard.press("Enter")
                logger.info("GM: CEP submitted via Enter")

            await self._wait_for_post_submit()

            # Verify CEP was applied
            if await self._verify_cep(page):
                logger.info("GM: CEP confirmed successfully", cep=CEP)
                return True

            logger.warning("GM: CEP submitted but verification inconclusive")
            return True  # Continue anyway — prices may still show

        return False

    async def _verify_cep(self, page: Page) -> bool:
        """Verify the CEP is now showing on the page."""
        try:
            body_text = await page.inner_text("body")
            formatted_cep = f"{CEP[:5]}-{CEP[5:]}"  # 80220-001
            if formatted_cep in body_text or CEP in body_text:
                return True
            # Check localStorage
            cep_str = await page.evaluate("() => window.localStorage.getItem('CEP')")
            if cep_str and ("80220" in str(cep_str) or "ODAyM" in str(cep_str)):
                return True
        except Exception:
            pass
        return False

    async def _is_session_valid(self, page: Page) -> bool:
        """Check if dealership CEP has been set in this session."""
        try:
            await page.goto(self.base_url, wait_until="domcontentloaded", timeout=30000)
            await self._wait_for_page_settle()
            body_text = await page.inner_text("body")
            formatted_cep = f"{CEP[:5]}-{CEP[5:]}"
            return formatted_cep in body_text or CEP in body_text
        except Exception:
            return False

    async def search_sku(self, page: Page, sku: str, brand: str = "") -> list[PartResult]:
        """Search for a part SKU on Chevrolet Parts and extract results.

        Strategy:
        1. Navigate to the direct search URL with the SKU in the part-number field
        2. Wait for product listing to render
        3. For each product card, navigate to the details page
        4. Extract all dealer/shop prices from the details page
        5. Return one PartResult per dealer/price combination
        """
        results: list[PartResult] = []

        try:
            search_url = (
                f"{BASE_URL}/pesquisa/"
                f"?nomepeca=&grupo=&nomeveiculo=&ano=&numeropeca={sku}"
            )
            logger.info("GM search: navigating", sku=sku, url=search_url)

            await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
            await self._wait_for_page_settle()

            # Check for blocked page
            if await self._detect_blocked(page):
                logger.warning("GM: blocked during search", sku=sku)
                return []

            # Check for "no results" indicators
            page_text = await page.inner_text("body")
            no_results_indicators = [
                "nenhum resultado",
                "nenhum produto encontrado",
                "não encontramos",
                "sem resultados",
                "nenhuma peça",
            ]
            if any(indicator in page_text.lower() for indicator in no_results_indicators):
                logger.info("GM search: no results found", sku=sku)
                return []

            # Find product cards/links in the search results
            product_links = await self._find_product_links(page)

            if not product_links:
                # We might already be on a single product page
                details_results = await self._extract_details_page(page, sku)
                if details_results:
                    results.extend(details_results)
                else:
                    logger.info("GM search: no product cards found", sku=sku)
                return results

            # Navigate into each product details page (limit to 5)
            for link_info in product_links[:5]:
                try:
                    detail_results = await self._navigate_and_extract_details(
                        page, link_info, sku
                    )
                    results.extend(detail_results)
                except Exception as e:
                    logger.warning(
                        "GM: failed to extract product details",
                        sku=sku, url=link_info.get("url", ""), error=str(e),
                    )

            logger.info("GM search completed", sku=sku, results_count=len(results))

        except Exception as e:
            logger.error("GM search failed", sku=sku, error=str(e))

        return results

    async def _find_product_links(self, page: Page) -> list[dict[str, Any]]:
        """Find product card links in search results. Returns list of {url, title}."""
        data = await page.evaluate("""() => {
            const links = [];
            // Look for product cards with links
            const selectors = [
                'a[href*="/p"]', 'a[href*="/produto"]',
                'div.product-card a', 'div.shelf-item a',
                'section[class*="product"] a',
                'div[class*="vtex-search-result"] a',
                'div[class*="product-summary"] a',
            ];
            const seen = new Set();
            for (const sel of selectors) {
                for (const el of document.querySelectorAll(sel)) {
                    const href = el.getAttribute('href');
                    if (!href || seen.has(href)) continue;
                    // Only product page links (not category/filter links)
                    if (href.includes('/p') || href.includes('/produto') || href.includes('/pesquisa')) {
                        seen.add(href);
                        links.push({
                            url: href.startsWith('http') ? href : location.origin + href,
                            title: el.textContent.trim().substring(0, 200),
                        });
                    }
                }
            }
            return links;
        }""")
        return data or []

    async def _navigate_and_extract_details(
        self, page: Page, link_info: dict[str, Any], searched_sku: str
    ) -> list[PartResult]:
        """Navigate to a product details page and extract all dealer/shop prices."""
        url = link_info.get("url", "")
        if not url:
            return []

        logger.info("GM: opening product details", url=url)
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await self._wait_for_dealer_prices(page)

        return await self._extract_details_page(page, searched_sku)

    async def _wait_for_dealer_prices(self, page: Page) -> None:
        """Wait for GM's dealer-price widget to finish rendering."""
        await self._wait_for_page_settle()
        try:
            await page.wait_for_selector(
                ".tab-precos-row-2024, .concessionaria-preco-2024-value",
                timeout=9000,
            )
        except Exception:
            logger.debug("GM: dealer price widget did not appear before extraction")
        await self._wait_for_page_settle(1200, 2600)

    async def _extract_details_page(self, page: Page, searched_sku: str) -> list[PartResult]:
        """Extract all prices and shop/dealer info from a product details page.

        Returns one PartResult per dealer/shop/price found.
        """
        results: list[PartResult] = []

        # Extract product title
        title = ""
        title_selectors = [
            "h1.product-name", "h1[class*='productName']",
            "h1.product-title", "h1",
            "span.vtex-product-identifier-0-x-product-identifier__value",
        ]
        for sel in title_selectors:
            el = await page.query_selector(sel)
            if el:
                title = (await el.inner_text()).strip()
                if title:
                    break

        if not title:
            return []

        product_url = page.url

        # Try to find part number / SKU on the page
        sku_found = searched_sku
        page_text = await page.inner_text("body")
        sku_match = re.search(
            r'(?:Código|Ref|SKU|Cód|Part\s*Number)[:\s]*([A-Za-z0-9\-\.]{4,25})',
            page_text, re.I
        )
        if sku_match:
            sku_found = sku_match.group(1).strip()

        # Extract availability
        availability = await self._extract_availability(page)

        # Strategy 1: Multiple dealer/shop rows (table, list, or card sections)
        dealers = await self._extract_dealer_rows(page)

        if dealers:
            for dealer in dealers:
                results.append(PartResult(
                    sku_searched=searched_sku,
                    sku_found=sku_found,
                    exact_match=self.validate_exact_match(searched_sku, sku_found),
                    site=self.site_id,
                    site_name=self.site_name,
                    price=dealer.get("price", 0.0),
                    currency=Currency.BRL,
                    condition=ItemCondition.NEW,
                    availability=dealer.get("availability", availability),
                    seller_name=dealer.get("name", "Chevrolet (official)"),
                    product_url=product_url,
                    origin="Brasil",
                    raw_title=title,
                ))
        else:
            price = await self._extract_price(page)
            if price is None:
                return []
            results.append(PartResult(
                sku_searched=searched_sku,
                sku_found=sku_found,
                exact_match=self.validate_exact_match(searched_sku, sku_found),
                site=self.site_id,
                site_name=self.site_name,
                price=price,
                currency=Currency.BRL,
                condition=ItemCondition.NEW,
                availability=availability,
                seller_name="Chevrolet (official)",
                product_url=product_url,
                origin="Brasil",
                raw_title=title,
            ))

        logger.info(
            "GM: details page extracted",
            sku=searched_sku, title=title[:60],
            dealers=len(dealers), total_results=len(results),
        )
        return results

    async def _extract_dealer_rows(self, page: Page) -> list[dict[str, Any]]:
        """Extract all dealer/shop rows from a product details page.

        Returns list of {name, price, availability} dicts.
        """
        data = await page.evaluate("""() => {
            const dealers = [];

            // Current 2024 details page layout.
            for (const row of document.querySelectorAll('.tab-precos-row-2024')) {
                const text = row.textContent || '';
                const priceEl = row.querySelector('.concessionaria-preco-2024-value');
                const nameEl = row.querySelector('.concessionaria-name-2024');
                const cityEl = row.querySelector('.concessionaria-cidade-2024');
                const distanceEl = row.querySelector('.concessionaria-distancia-2024');
                const priceText = priceEl ? priceEl.textContent.trim() : '';
                const fallbackPrice = text.match(/Preço\\s*\\(R\\$\\)\\s*:\\s*([\\d.,]+)/i);
                if (!priceText && !fallbackPrice) continue;

                dealers.push({
                    name: nameEl ? nameEl.textContent.trim() : '',
                    city: cityEl ? cityEl.textContent.trim() : '',
                    distance: distanceEl ? distanceEl.textContent.trim() : '',
                    price: priceText || fallbackPrice[1],
                    availability: text.includes('COMPRAR') ? 'Disponível' : 'unknown',
                });
            }

            if (dealers.length > 0) return dealers;

            // Strategy 1: Look for seller/dealer sections, tables, or cards
            const selectors = [
                '[class*="seller"]', '[class*="dealer"]', '[class*="loja"]',
                '[class*="concession"]', '[class*="shop"]', '[class*="store"]',
                'table[class*="seller"] tr', 'table[class*="dealer"] tr',
                '[class*="vendor-list"] > *', '[class*="sellerList"] > *',
                '[class*="vtex-seller"] > *',
            ];

            for (const sel of selectors) {
                const elements = document.querySelectorAll(sel);
                if (elements.length === 0) continue;

                for (const el of elements) {
                    const text = el.textContent || '';
                    const priceMatch = text.match(/R\\$\\s*([\\d.,]+)/);
                    if (!priceMatch) continue;

                    // Extract dealer/shop name
                    const nameEl = el.querySelector(
                        '[class*="name"], [class*="title"], [class*="seller"], ' +
                        'strong, b, h3, h4, td:first-child'
                    );
                    const name = nameEl
                        ? nameEl.textContent.trim()
                        : text.split('\\n').filter(l => l.trim().length > 3 && !l.includes('R$'))[0]?.trim() || '';

                    // Extract availability
                    const availEl = el.querySelector(
                        '[class*="stock"], [class*="availability"], [class*="estoque"]'
                    );
                    const availability = availEl ? availEl.textContent.trim() : 'unknown';

                    dealers.push({
                        name: name.substring(0, 200),
                        price: priceMatch[1],
                        availability: availability.substring(0, 100),
                    });
                }
                if (dealers.length > 0) break;  // Use first matching strategy
            }

            // Strategy 2: Look for multiple R$ price blocks as separate offers
            if (dealers.length === 0) {
                const priceBlocks = document.querySelectorAll(
                    '[class*="price-block"], [class*="oferta"], ' +
                    '[class*="sellingPrice"], [class*="offer"]'
                );
                for (const block of priceBlocks) {
                    const text = block.textContent || '';
                    const priceMatch = text.match(/R\\$\\s*([\\d.,]+)/);
                    if (!priceMatch) continue;
                    const parent = block.closest('div, section, li, tr');
                    const parentText = parent ? parent.textContent : text;
                    const nameMatch = parentText.match(
                        /(?:vendido por|loja|seller|concession[áa]ria)[:\\s]*([^\\n]{3,50})/i
                    );
                    dealers.push({
                        name: nameMatch ? nameMatch[1].trim() : '',
                        price: priceMatch[1],
                        availability: 'unknown',
                    });
                }
            }

            return dealers;
        }""")

        parsed = []
        for d in (data or []):
            price = self._parse_price(d.get("price", ""))
            if price is not None:
                name_parts = [
                    d.get("name", ""),
                    d.get("city", ""),
                    d.get("distance", ""),
                ]
                parsed.append({
                    "name": " - ".join(part for part in name_parts if part),
                    "price": price,
                    "availability": d.get("availability", "unknown"),
                })
        return parsed

    async def _extract_price(self, page: Page) -> float | None:
        """Extract price from the current page (single product view)."""
        price_selectors = [
            ".concessionaria-preco-2024-value",
            "span[class*='sellingPrice'] span[class*='currencyInteger']",
            "span.vtex-product-price-1-x-sellingPriceValue",
            "span.price-best-price",
            "strong.skuBestPrice",
            "span[class*='Price'] span",
            "span.price",
            "div.price",
        ]
        for selector in price_selectors:
            el = await page.query_selector(selector)
            if el:
                text = await el.inner_text()
                price = self._parse_price(text)
                if price and price > 0:
                    return price
        return None

    async def _extract_availability(self, page: Page) -> str:
        """Extract availability from the current page."""
        selectors = [
            "span[class*='stock']",
            "div[class*='availability']",
            "span.availability",
            "button[class*='buy']",
        ]
        for selector in selectors:
            el = await page.query_selector(selector)
            if el:
                text = (await el.inner_text()).strip()
                if text:
                    return text

        body_text = await page.inner_text("body")
        lower_text = body_text.lower()
        if "esgotado" in lower_text or "indisponível" in lower_text:
            return "Estoque esgotado"
        if "comprar" in lower_text or "adicionar" in lower_text:
            return "Disponível"

        return "unknown"

    @staticmethod
    def _parse_price(price_text: str) -> float | None:
        return BaseScraper.parse_brazilian_price(price_text)
