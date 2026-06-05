"""Peça Direta scraper — pecadireta.com.br.

Site characteristics:
- Platform: Custom SPA (React/Vue), client-side rendered
- Search: URL-based — /procurar/pecas?query={SKU} (GET request)
- No login required for search (public marketplace)
- Has location-based filtering (CEP) — must check/update
- Marketplace connecting buyers with multiple sellers/suppliers

Key business rules:
- Price in BRL (R$ format)
- Multiple sellers may have the same part at different prices
- Product titles contain part number code
- Condition varies (new, used, remanufactured)
- Must click into product detail page for full info
"""

import re
from typing import Any
from urllib.parse import urlparse

import structlog
from playwright.async_api import Page

from src.models.schemas import Currency, ItemCondition, PartResult, SiteId
from src.scrapers.base import BaseScraper

logger = structlog.get_logger()

BASE_URL = "https://www.pecadireta.com.br"
SEARCH_URL = f"{BASE_URL}/procurar/pecas"
CEP = "80220001"


class PecaDiretaScraper(BaseScraper):
    """Scraper for Peça Direta — automotive parts marketplace.

    This is a public marketplace (aggregator with multiple sellers).
    No authentication required for search.

    Search flow:
        1. Navigate to /procurar/pecas?query={SKU}
        2. Check/update CEP for location-based pricing
        3. Click into product result for detail extraction
        4. Extract all sellers, prices, and product information
    """

    @property
    def site_id(self) -> SiteId:
        return SiteId.PECA_DIRETA

    @property
    def site_name(self) -> str:
        return "Peça Direta"

    @property
    def base_url(self) -> str:
        return BASE_URL

    async def login(self, page: Page) -> bool:
        """No authentication required for search."""
        return True

    async def _is_session_valid(self, page: Page) -> bool:
        """Always valid — no session to expire."""
        return True

    async def _check_and_update_cep(self, page: Page) -> None:
        """Check the CEP box on the page and update it with our CEP if needed."""
        try:
            # Look for CEP input/display elements
            cep_selectors = [
                'input[placeholder*="CEP"]',
                'input[name*="cep"]',
                'input[id*="cep"]',
                'input[class*="cep"]',
            ]
            for selector in cep_selectors:
                cep_input = page.locator(selector).first
                if await cep_input.is_visible():
                    current_val = await cep_input.input_value()
                    formatted_cep = f"{CEP[:5]}-{CEP[5:]}"

                    if CEP in (current_val or "") or formatted_cep in (current_val or ""):
                        logger.info("PeçaDireta: CEP already set", cep=CEP)
                        return

                    # Update CEP
                    await cep_input.click()
                    await self._wait_for_micro_interaction()
                    await cep_input.fill("")
                    await cep_input.fill(CEP)
                    await self._wait_for_micro_interaction()
                    logger.info("PeçaDireta: CEP filled", cep=CEP)

                    # Try to confirm/submit
                    confirm_btn = (
                        page.locator("button")
                        .filter(has_text=re.compile(r"OK|Confirmar|Atualizar|Buscar|Aplicar", re.I))
                        .first
                    )
                    if await confirm_btn.is_visible():
                        await confirm_btn.click()
                        logger.info("PeçaDireta: CEP confirmed via button")
                    else:
                        await page.keyboard.press("Enter")
                        logger.info("PeçaDireta: CEP confirmed via Enter")

                    await self._wait_for_post_submit()

                    # Verify
                    body_text = await page.inner_text("body")
                    if CEP in body_text or formatted_cep in body_text:
                        logger.info("PeçaDireta: CEP verified on page", cep=CEP)
                    else:
                        logger.info("PeçaDireta: CEP submitted, verification inconclusive")
                    return

            # Try clicking a CEP-related button/link to open CEP input
            cep_trigger = (
                page.locator("button, a, div, span")
                .filter(has_text=re.compile(r"CEP|Localização|Região|Onde você está", re.I))
                .first
            )
            if await cep_trigger.is_visible():
                await cep_trigger.click()
                await self._wait_for_page_settle()
                # Retry finding CEP input after opening
                for selector in cep_selectors:
                    cep_input = page.locator(selector).first
                    if await cep_input.is_visible():
                        await cep_input.click()
                        await cep_input.fill("")
                        await cep_input.fill(CEP)
                        await page.keyboard.press("Enter")
                        await self._wait_for_post_submit()
                        logger.info("PeçaDireta: CEP updated after opening dialog", cep=CEP)
                        return

            logger.info("PeçaDireta: no CEP input found on page, continuing")

        except Exception as e:
            logger.warning("PeçaDireta: CEP update failed, continuing", error=str(e))

    async def search_sku(self, page: Page, sku: str, brand: str = "") -> list[PartResult]:
        """Search for a part SKU on Peça Direta.

        Flow:
        1. Navigate to search URL
        2. Check/update CEP
        3. Find product results
        4. Click into product detail pages
        5. Extract all sellers and prices
        """
        url = f"{SEARCH_URL}?query={sku}"
        logger.info("Searching Peça Direta", sku=sku, url=url)

        await page.goto(url, wait_until="domcontentloaded", timeout=20000)
        await self._wait_for_results(
            page,
            '[class*="card"], [class*="product"], [class*="anuncio"], '
            '[class*="result"], [class*="listing"], article',
            timeout_ms=10000,
        )

        # Check/update CEP
        await self._check_and_update_cep(page)

        # Check for blocked page
        if await self._detect_blocked(page):
            logger.warning("PeçaDireta: blocked during search", sku=sku)
            return []

        # Check for no results
        body_text = await page.inner_text("body")
        no_results_phrases = [
            "nenhum resultado",
            "não encontramos",
            "nenhum anúncio",
            "nenhuma peça",
            "sem resultados",
        ]
        if any(phrase in body_text.lower() for phrase in no_results_phrases):
            logger.info("PeçaDireta: no results found", sku=sku)
            return []

        listing_results = await self._extract_listing_cards(page, sku)
        if listing_results:
            priced_listing = [r for r in listing_results if r.price is not None and r.price > 0]
            if priced_listing:
                logger.info(
                    "PeçaDireta: extracted priced listing cards",
                    sku=sku,
                    count=len(priced_listing),
                )
                return priced_listing

            for r in listing_results:
                if not r.exact_match:
                    continue
                purl = (r.product_url or "").strip()
                if not purl or "/produto/" not in purl:
                    continue
                if r.price is not None and r.price > 0:
                    continue
                try:
                    detail = await self._navigate_and_extract_product(
                        page,
                        {"url": purl, "title": r.raw_title or ""},
                        sku,
                    )
                except Exception as e:
                    logger.warning(
                        "PeçaDireta: detail open failed after unpriced listing",
                        sku=sku,
                        url=purl,
                        error=str(e),
                    )
                    await page.goto(url, wait_until="domcontentloaded", timeout=20000)
                    await self._wait_for_page_settle()
                    continue
                priced_detail = [x for x in detail if x.price is not None and x.price > 0]
                if priced_detail:
                    logger.info(
                        "PeçaDireta: recovered prices from product page",
                        sku=sku,
                        url=purl,
                        count=len(priced_detail),
                    )
                    return priced_detail
                await page.goto(url, wait_until="domcontentloaded", timeout=20000)
                await self._wait_for_page_settle()

            logger.info(
                "PeçaDireta: exact listing without usable price or stock",
                sku=sku,
                count=len(listing_results),
            )
            return [r for r in listing_results if r.exact_match]

        # Find product links in search results
        product_links = await self._find_product_links(page)

        if not product_links:
            logger.info("PeçaDireta: no product links found", sku=sku)
            return []

        # Click into each product and extract details (limit to 5)
        results: list[PartResult] = []
        for link_info in product_links[:5]:
            try:
                detail_results = await self._navigate_and_extract_product(page, link_info, sku)
                results.extend(detail_results)
            except Exception as e:
                logger.warning(
                    "PeçaDireta: failed extracting product",
                    sku=sku,
                    url=link_info.get("url", ""),
                    error=str(e),
                )

            # Navigate back to search results for next product
            await page.goto(url, wait_until="domcontentloaded", timeout=20000)
            await self._wait_for_page_settle()

        logger.info("PeçaDireta: search completed", sku=sku, count=len(results))
        return results

    async def _find_product_links(self, page: Page) -> list[dict[str, Any]]:
        """Find clickable product links in search results."""
        data = await page.evaluate("""() => {
            const links = [];
            const seen = new Set();
            const origin = location.origin;

            // Only same-site product detail URLs are safe. Pagination, footer,
            // social, WhatsApp, and help links can appear inside generic cards.
            const selectors = [
                'a[href^="/produto/"]',
                'a[href^="https://www.pecadireta.com.br/produto/"]',
            ];

            for (const sel of selectors) {
                for (const el of document.querySelectorAll(sel)) {
                    const href = el.getAttribute('href');
                    if (!href || seen.has(href) || href === '#') continue;
                    const url = href.startsWith('http') ? href : origin + href;
                    try {
                        const parsed = new URL(url);
                        if (parsed.origin !== origin || !parsed.pathname.startsWith('/produto/')) {
                            continue;
                        }
                    } catch {
                        continue;
                    }
                    seen.add(url);
                    links.push({
                        url: url,
                        title: el.textContent.trim().substring(0, 200),
                    });
                }
            }
            return links;
        }""")
        return data or []

    async def _navigate_and_extract_product(
        self, page: Page, link_info: dict[str, Any], searched_sku: str
    ) -> list[PartResult]:
        """Navigate to a product page and extract all available info."""
        url = link_info.get("url", "")
        if not url:
            return []

        logger.info("PeçaDireta: opening product page", url=url)
        await page.goto(url, wait_until="domcontentloaded", timeout=20000)
        await self._action_delay()
        await self._wait_for_page_settle()

        return await self._extract_product_page(page, searched_sku)

    async def _extract_product_page(self, page: Page, searched_sku: str) -> list[PartResult]:
        """Extract all info from a product detail page — all sellers and prices."""
        results: list[PartResult] = []

        data = await page.evaluate(
            """(searchedSku) => {
            const info = {
                title: '',
                sku: '',
                sellers: [],
                mainPrice: '',
                condition: 'unknown',
                availability: 'unknown',
                url: location.href,
            };

            // Title
            const titleEl = document.querySelector(
                'h1, h2, [class*="title"], [class*="name"], [class*="descri"]'
            );
            info.title = titleEl ? titleEl.textContent.trim().substring(0, 300) : '';

            // SKU/part number
            const bodyText = document.body ? document.body.textContent : '';
            const refMatch = bodyText.match(
                /(?:REF[.:]*|Código:?|Cód[.:]*|Part[.:]*|Ref[.:]*|Referência:?)\\s*([A-Za-z0-9.\\-]{4,25})/i
            );
            if (refMatch) {
                info.sku = refMatch[1].replace(/^[.]/, '').toUpperCase();
            }

            // Condition
            const condText = bodyText.toLowerCase();
            if (condText.includes('genuín') || condText.includes('original') || condText.includes('novo')) {
                info.condition = 'new';
            } else if (condText.includes('usado') || condText.includes('semi-novo')) {
                info.condition = 'used';
            }
            if (
                condText.includes('sem estoque') ||
                condText.includes('fora de estoque') ||
                condText.includes('temporariamente fora') ||
                condText.includes('indisponível') ||
                condText.includes('esgotado')
            ) {
                info.availability = 'Sem estoque';
            } else if (condText.includes('disponível') || condText.includes('comprar')) {
                info.availability = 'Disponível';
            }

            // Find all seller/price blocks
            const sellerSelectors = [
                '[class*="seller"]', '[class*="vendor"]', '[class*="fornecedor"]',
                '[class*="loja"]', '[class*="store"]', '[class*="offer"]',
                '[class*="anuncio"]', '[class*="card"]',
            ];

            for (const sel of sellerSelectors) {
                const elements = document.querySelectorAll(sel);
                for (const el of elements) {
                    const text = el.textContent || '';
                    const priceMatch = text.match(/R\\$\\s*([\\d.,]+)/);
                    if (!priceMatch) continue;

                    const nameEl = el.querySelector(
                        '[class*="name"], [class*="seller"], [class*="loja"], ' +
                        'strong, b, h3, h4'
                    );
                    const name = nameEl ? nameEl.textContent.trim() : '';

                    const locationEl = el.querySelector(
                        '[class*="city"], [class*="local"], [class*="estado"], [class*="cidade"]'
                    );
                    const location = locationEl ? locationEl.textContent.trim() : '';

                    const availEl = el.querySelector(
                        '[class*="stock"], [class*="disponib"], [class*="pronta"]'
                    );
                    const availability = availEl ? availEl.textContent.trim() : 'unknown';
                    const cnpjMatch = text.match(
                        /\\d{2}\\.?\\d{3}\\.?\\d{3}\\/?\\d{4}-?\\d{2}/
                    );

                    info.sellers.push({
                        name: name.substring(0, 200),
                        price: priceMatch[1],
                        location: location.substring(0, 100),
                        cnpj: cnpjMatch ? cnpjMatch[0] : '',
                        availability: availability.substring(0, 100),
                    });
                }
                if (info.sellers.length > 0) break;
            }

            // Fallback: main page price if no seller blocks found
            if (info.sellers.length === 0) {
                const priceMeta = document.querySelector('meta[itemprop="price"][content]');
                if (priceMeta) {
                    const raw = (priceMeta.getAttribute('content') || '').trim();
                    const br = raw.match(/R\\$\\s*([\\d.,]+)/);
                    if (br) {
                        info.mainPrice = br[1];
                    } else if (raw && /\\d/.test(raw)) {
                        info.mainPrice = raw.replace(/[^\\d.,]/g, '');
                    }
                }
            }
            if (info.sellers.length === 0 && !info.mainPrice) {
                const ip = document.querySelector('[itemprop="price"]');
                if (ip) {
                    const c = (ip.getAttribute('content') || ip.textContent || '').trim();
                    const br = c.match(/R\\$\\s*([\\d.,]+)/);
                    if (br) info.mainPrice = br[1];
                }
            }
            if (info.sellers.length === 0 && !info.mainPrice) {
                const allPrices = [...(bodyText.matchAll(/R\\$\\s*([\\d]{1,3}(?:\\.\\d{3})*,\\d{2}|\\d+(?:[,\\.]\\d+)?)/g) || [])];
                if (allPrices.length > 0) {
                    info.mainPrice = allPrices[0][1];
                }
            }

            return info;
        }""",
            searched_sku,
        )

        title = data.get("title", "")
        found_sku = data.get("sku", "")
        product_url = data.get("url", str(page.url))
        condition_str = data.get("condition", "unknown")
        condition = {
            "new": ItemCondition.NEW,
            "used": ItemCondition.USED,
        }.get(condition_str, ItemCondition.UNKNOWN)

        # Determine exact match
        if not found_sku and (
            self._contains_sku(title, searched_sku)
            or self._contains_sku_in_path(product_url, searched_sku)
        ):
            found_sku = searched_sku

        exact = self.validate_exact_match(searched_sku, found_sku) if found_sku else False

        sellers = data.get("sellers", [])
        if sellers:
            for seller in sellers:
                price = self._parse_price(seller.get("price", ""))
                results.append(
                    PartResult(
                        sku_searched=searched_sku,
                        sku_found=found_sku or searched_sku,
                        exact_match=exact,
                        site=self.site_id,
                        site_name=self.site_name,
                        price=price,
                        currency=Currency.BRL,
                        condition=condition,
                        availability=seller.get("availability", "unknown"),
                        seller_name=seller.get("name", ""),
                        seller_uf=self.extract_brazil_uf(seller.get("location", "")),
                        seller_company_name=seller.get("name", ""),
                        seller_cnpj=self.extract_cnpj_digits(seller.get("cnpj", "")),
                        product_url=product_url,
                        origin="Brasil",
                        raw_title=title,
                    )
                )
        else:
            main_price = self._parse_price(data.get("mainPrice", ""))
            if title:
                results.append(
                    PartResult(
                        sku_searched=searched_sku,
                        sku_found=found_sku or searched_sku,
                        exact_match=exact,
                        site=self.site_id,
                        site_name=self.site_name,
                        price=main_price,
                        currency=Currency.BRL,
                        condition=condition,
                        availability=data.get("availability", "unknown"),
                        seller_name="",
                        product_url=product_url,
                        origin="Brasil",
                        raw_title=title,
                    )
                )

        return results

    async def _extract_listing_cards(self, page: Page, searched_sku: str) -> list[PartResult]:
        """Fallback: extract results from listing cards without navigating to detail."""
        data = await page.evaluate(
            """(searchedSku) => {
            const results = [];
            const cards = document.querySelectorAll(
                'div.card-produto-horizontal, [class*="produto-horizontal"], ' +
                '[class*="product-card"], [class*="card-product"], article'
            );

            for (const card of cards) {
                const text = card.textContent || '';
                const linkEl = card.querySelector(
                    'a[href^="/produto/"], a[href*="pecadireta.com.br/produto/"]'
                );
                const href = linkEl ? linkEl.getAttribute('href') || '' : '';
                if (!href) continue;

                const titleEl = card.querySelector(
                    'h1, h2, h3, h4, h5, [class*="title"], [class*="name"]'
                );
                const title = titleEl
                    ? titleEl.textContent.trim()
                    : (linkEl.textContent || '').trim();
                const priceMatch = text.match(/R\\$\\s*([\\d.,]+)/);

                const sellerEl = card.querySelector(
                    '[class*="seller"], [class*="vendor"], [class*="loja"]'
                );
                const seller = sellerEl ? sellerEl.textContent.trim() : '';
                const locationEl = card.querySelector(
                    '[class*="city"], [class*="local"], [class*="estado"], [class*="cidade"]'
                );
                const location = locationEl ? locationEl.textContent.trim() : '';
                const cnpjMatch = text.match(
                    /\\d{2}\\.?\\d{3}\\.?\\d{3}\\/?\\d{4}-?\\d{2}/
                );
                const cnpj = cnpjMatch ? cnpjMatch[0] : '';

                const condText = text.toLowerCase();
                let condition = 'unknown';
                if (condText.includes('novo') || condText.includes('original') || condText.includes('genuín')) {
                    condition = 'new';
                } else if (condText.includes('usado')) {
                    condition = 'used';
                }

                let availability = 'unknown';
                if (
                    condText.includes('sem estoque') ||
                    condText.includes('fora de estoque') ||
                    condText.includes('temporariamente fora') ||
                    condText.includes('indisponível') ||
                    condText.includes('esgotado')
                ) {
                    availability = 'Sem estoque';
                } else if (condText.includes('disponível') || condText.includes('comprar')) {
                    availability = 'Disponível';
                }

                results.push({
                    price: priceMatch ? priceMatch[1] : '',
                    title: title.substring(0, 200),
                    url: href,
                    seller: seller.substring(0, 100),
                    location: location.substring(0, 100),
                    cnpj: cnpj,
                    condition: condition,
                    availability: availability,
                });
                if (results.length >= 20) break;
            }
            return results;
        }""",
            searched_sku,
        )

        results: list[PartResult] = []
        for item in data or []:
            price = self._parse_price(item.get("price", ""))
            raw_title = item.get("title", "")
            href = item.get("url", "")
            product_url = ""
            if href:
                product_url = href if href.startswith("http") else f"{BASE_URL}{href}"

            found_sku = ""
            if self._contains_sku(raw_title, searched_sku) or (
                href and self._contains_sku_in_path(href, searched_sku)
            ):
                found_sku = searched_sku
            elif href:
                found_sku = self._sku_from_product_path(href)

            condition = {
                "new": ItemCondition.NEW,
                "used": ItemCondition.USED,
            }.get(item.get("condition", "unknown"), ItemCondition.UNKNOWN)

            exact = self.validate_exact_match(searched_sku, found_sku) if found_sku else False

            results.append(
                PartResult(
                    sku_searched=searched_sku,
                    sku_found=found_sku or searched_sku,
                    exact_match=exact,
                    site=self.site_id,
                    site_name=self.site_name,
                    price=price,
                    currency=Currency.BRL,
                    condition=condition,
                    availability=item.get("availability", "unknown"),
                    seller_name=item.get("seller", ""),
                    seller_uf=self.extract_brazil_uf(item.get("location", "")),
                    seller_company_name=item.get("seller", ""),
                    seller_cnpj=self.extract_cnpj_digits(item.get("cnpj", "")),
                    product_url=product_url or str(page.url),
                    origin="Brasil",
                    raw_title=raw_title,
                )
            )

        return results

    @staticmethod
    def _parse_price(price_text: str) -> float | None:
        return BaseScraper.parse_brazilian_price(price_text)

    @staticmethod
    def _contains_sku(text: str, searched_sku: str) -> bool:
        return BaseScraper.contains_sku(text, searched_sku)

    @classmethod
    def _contains_sku_in_path(cls, href: str, searched_sku: str) -> bool:
        if not href:
            return False
        return cls._contains_sku(urlparse(href).path, searched_sku)

    @staticmethod
    def _sku_from_product_path(href: str) -> str:
        """Extract SKU-like segment from /produto/{brand}/{sku} URLs."""
        path_parts = [part for part in urlparse(href).path.split("/") if part]
        if len(path_parts) >= 3 and path_parts[0] == "produto":
            return re.sub(r"[^A-Za-z0-9.\-/]", "", path_parts[2]).upper()
        return ""
