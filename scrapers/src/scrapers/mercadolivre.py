"""Mercado Livre marketplace scraper.

- Search URL: https://lista.mercadolivre.com.br/{SKU}_NoIndex_True
- Results container: div.ui-search-results
- Result card: div.ui-search-result, li.ui-search-layout__item
- Title: h2.ui-search-item__title
- Price integer: span.andes-money-amount__fraction
- Price cents: span.andes-money-amount__cents
- Condition: shown as "Novo" or "Usado" in listing

Business rules:
- Only return items with condition == "Novo" (new)
- Exact SKU match required — ML returns similar items by default
- Search via public search (no login for MVP)
- Brazilian prices in BRL
- ML has bot detection — use stealth user-agent and random delays
"""

import contextlib
import re
from urllib.parse import unquote

import structlog
from playwright.async_api import Page

from src.models.schemas import Currency, ItemCondition, PartResult, SiteId
from src.scrapers.base import BaseScraper

logger = structlog.get_logger()

ML_HOME_URL = "https://www.mercadolivre.com.br"
ML_LIST_URL = "https://lista.mercadolivre.com.br"
ML_PRODUCT_BASE = "https://produto.mercadolivre.com.br"
ML_CEP = "80220001"
# Detail-page hops caused noisy tab churn in headed demos; cards + URL evidence are enough.
ML_DETAIL_CHECK_LIMIT = 0
# Exact SKU matches often appear after sponsored/related cards (typically index 10+).
# Scan every card on the results page — do not stop after the first priced hit.
ML_MAX_CARDS_TO_SCAN = 120
ML_BLOCKED_TEXT_INDICATORS = (
    "captcha",
    "recaptcha",
    "turnstile",
    "verificação de segurança",
    "verificacao de seguranca",
    "access denied",
    "acesso negado",
    "too many requests",
    "rate limit",
    "por favor, tente novamente",
    "verify you are human",
    "please verify you are a human",
    "checking your browser",
    "just a moment",
    "cloudflare",
    "anti-bot",
    "robot",
    "robô",
    "robo",
    "desafio de segurança",
    "desafio de seguranca",
    "identidade",
)
ML_BLOCKED_SELECTOR = (
    "#challenge-running, #challenge-form, "
    "iframe[src*='captcha'], iframe[src*='recaptcha'], iframe[src*='challenge'], "
    "iframe[src*='turnstile'], input[name='cf-turnstile-response'], "
    "div[class*='captcha'], div[class*='challenge'], div[class*='security']"
)


class MercadoLivreScraper(BaseScraper):
    """Scraper for Mercado Livre marketplace — public search, no login.

    IMPORTANT: Mercado Livre has aggressive bot detection (Cloudflare + custom
    fingerprinting). This scraper uses:
    - Standard Chrome user-agent (set in BaseScraper)
    - Random delays between actions
    - domcontentloaded wait (not networkidle — ML has infinite requests)

    Search flow:
        1. Open mercadolivre.com.br and set CEP when prompted
        2. Navigate to lista search URL for the SKU
        3. Extract product cards from the results grid
        4. Filter: only "Novo" (new) items
        5. Validate: SKU appears in title, card text, or URL
    """

    @property
    def site_id(self) -> SiteId:
        return SiteId.MERCADO_LIVRE

    @property
    def site_name(self) -> str:
        return "Mercado Livre"

    @property
    def base_url(self) -> str:
        return ML_HOME_URL

    async def login(self, page: Page) -> bool:
        """Open ML home and set CEP so lista search returns localized prices."""
        try:
            await page.goto(ML_HOME_URL, wait_until="domcontentloaded", timeout=30000)
            await self._wait_for_page_settle(1500, 3000)
            await self._ensure_cep(page)
            return True
        except Exception as e:
            logger.warning("ML login: CEP setup failed", error=str(e))
            return True

    async def _is_session_valid(self, page: Page) -> bool:
        """Session is valid when CEP is already applied in this browser context."""
        try:
            formatted_cep = f"{ML_CEP[:5]}-{ML_CEP[5:]}"
            body_text = await page.inner_text("body")
            return ML_CEP in body_text or formatted_cep in body_text
        except Exception:
            return False

    async def _ensure_cep(self, page: Page) -> None:
        """Set delivery CEP on ML home before lista search."""
        formatted_cep = f"{ML_CEP[:5]}-{ML_CEP[5:]}"
        try:
            body_text = await page.inner_text("body")
            if ML_CEP in body_text or formatted_cep in body_text:
                logger.info("ML: CEP already set", cep=ML_CEP)
                return
        except Exception:
            body_text = ""

        cep_selectors = [
            'input[data-testid="zip-code-textfield"]',
            'input[placeholder*="CEP"]',
            'input[name*="zipcode"]',
            'input[name*="cep"]',
            'input[id*="cep"]',
            'input[inputmode="numeric"]',
        ]
        for selector in cep_selectors:
            cep_input = page.locator(selector).first
            if not await cep_input.is_visible():
                continue
            current_val = await cep_input.input_value()
            if ML_CEP in (current_val or "") or formatted_cep in (current_val or ""):
                logger.info("ML: CEP input already filled", cep=ML_CEP)
                return

            await cep_input.click()
            await self._wait_for_micro_interaction()
            await cep_input.fill("")
            await cep_input.fill(ML_CEP)
            await self._wait_for_micro_interaction()
            logger.info("ML: CEP filled", cep=ML_CEP)

            confirm_btn = page.locator("button").filter(
                has_text=re.compile(r"Usar|Confirmar|OK|Continuar|Salvar", re.I)
            ).first
            if await confirm_btn.is_visible():
                await confirm_btn.click()
            else:
                await page.keyboard.press("Enter")
            await self._wait_for_post_submit()
            return

        cep_trigger = page.locator("button, a, span").filter(
            has_text=re.compile(r"CEP|Informe|Código postal|Onde comprar|Enviar para", re.I)
        ).first
        if await cep_trigger.is_visible():
            await cep_trigger.click()
            await self._wait_for_page_settle(1000, 2000)
            for selector in cep_selectors:
                cep_input = page.locator(selector).first
                if await cep_input.is_visible():
                    await cep_input.fill(ML_CEP)
                    await page.keyboard.press("Enter")
                    await self._wait_for_post_submit()
                    logger.info("ML: CEP set via dialog", cep=ML_CEP)
                    return

        logger.info("ML: no CEP control found on home, continuing to search")

    async def search_sku(self, page: Page, sku: str, brand: str = "") -> list[PartResult]:
        """Search Mercado Livre for a part by SKU.

        Business rules:
        1. Search using exact part number
        2. Filter out used items (condition != "Usado")
        3. Validate SKU match is exact (ML returns similar items)
        4. Return price in BRL with seller info
        """
        results: list[PartResult] = []

        try:
            if ML_HOME_URL not in page.url:
                await page.goto(ML_HOME_URL, wait_until="domcontentloaded", timeout=30000)
                await self._wait_for_page_settle(1500, 3000)
                await self._ensure_cep(page)

            search_url = f"{ML_LIST_URL}/{sku}_NoIndex_True"
            logger.info("ML search: navigating", sku=sku, url=search_url)

            await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
            await self._wait_for_page_settle(2000, 4000)

            # Check for CAPTCHA or access denied
            if await self._check_blocked(page):
                logger.warning("ML search: blocked by bot detection", sku=sku)
                return []

            # Check for "no results"
            no_results = await page.query_selector(
                "div.ui-search-rescue, "
                "p.ui-search-rescue__text, "
                "[class*='empty-state']"
            )
            if no_results:
                # Also check page text
                page_text = await page.inner_text("body")
                if "não encontramos" in page_text.lower() or "sem resultados" in page_text.lower():
                    logger.info("ML search: no results found", sku=sku)
                    return []

            # Check if we landed on a single product page (ML sometimes redirects)
            if ML_PRODUCT_BASE in page.url or "MLB-" in page.url:
                single = await self._extract_single_product(page, sku)
                if single:
                    results.append(single)
                return results

            # Prefer bulk DOM extraction (poly + andes layouts); fall back to per-card queries.
            results = await self._extract_results_via_dom(page, sku)
            if not results:
                result_cards = await self._find_result_cards(page)
                if not result_cards:
                    logger.info("ML search: no result cards found", sku=sku)
                    return []

                for card in result_cards[:ML_MAX_CARDS_TO_SCAN]:
                    try:
                        part_result = await self._extract_card_result(card, sku)
                        if part_result:
                            results.append(part_result)
                    except Exception as e:
                        logger.warning("ML: failed to extract card", sku=sku, error=str(e))
                        continue

            # Filter: only NEW items; keep every priced listing from the search page.
            results = self._filter_new_only(results)
            if ML_DETAIL_CHECK_LIMIT > 0 and not any(result.exact_match for result in results):
                await self._verify_candidate_detail_pages(page, results, sku)

            logger.info("ML search completed", sku=sku, results_count=len(results))

        except Exception as e:
            logger.error("ML search failed", sku=sku, error=str(e))

        return results

    async def _check_blocked(self, page: Page) -> bool:
        """Check if ML blocked our request (CAPTCHA, rate limit, etc.)."""
        return await self._detect_ml_blocked(page)

    async def _detect_blocked(self, page: Page) -> bool:
        """Detect shared and Mercado Livre-specific anti-bot/security blocks."""
        if await super()._detect_blocked(page):
            return True
        return await self._detect_ml_blocked(page)

    async def _detect_ml_blocked(self, page: Page) -> bool:
        """Check Mercado Livre-specific CAPTCHA/security/rate-limit signals."""
        try:
            page_text = (await page.inner_text("body")).lower()
        except Exception:
            page_text = ""

        if any(indicator in page_text for indicator in ML_BLOCKED_TEXT_INDICATORS):
            return True

        try:
            challenge = await page.query_selector(ML_BLOCKED_SELECTOR)
            if challenge:
                return True
        except Exception:
            return False

        return False

    async def _extract_results_via_dom(self, page: Page, searched_sku: str) -> list[PartResult]:
        """Extract listing rows in one DOM pass (faster and matches current poly layout)."""
        try:
            raw_cards = await page.evaluate(
                """(maxCards) => {
                    const selectors = [
                        'li.ui-search-layout__item',
                        'div.ui-search-result',
                        'div.ui-search-result__wrapper',
                        'li.poly-card',
                    ];
                    let cards = [];
                    for (const selector of selectors) {
                        const found = [...document.querySelectorAll(selector)];
                        if (found.length > cards.length) cards = found;
                    }
                    const slice = maxCards > 0 ? cards.slice(0, maxCards) : cards;
                    return slice.map((card) => {
                        const titleEl = card.querySelector(
                            'h2.ui-search-item__title, h2.poly-component__title, ' +
                            'a.ui-search-link__title-card, a.poly-component__title, a[class*="title"]'
                        );
                        const linkEl = card.querySelector(
                            'a.ui-search-link, a.ui-search-item__group__element, ' +
                            'a.poly-component__title, a[href*="mercadolivre.com.br"], a[href*="MLB"]'
                        );
                        const moneyEl = card.querySelector(
                            '.poly-price__current .andes-money-amount, ' +
                            '.andes-money-amount[aria-label], .andes-money-amount'
                        );
                        const fractionEl = card.querySelector(
                            'span.andes-money-amount__fraction, span.price-tag-fraction'
                        );
                        const centsEl = card.querySelector(
                            'span.andes-money-amount__cents, span.price-tag-cents'
                        );
                        return {
                            title: (titleEl?.textContent || '').trim(),
                            url: linkEl?.href || '',
                            cardText: (card.innerText || '').trim().slice(0, 1200),
                            fraction: (fractionEl?.textContent || '').trim(),
                            cents: (centsEl?.textContent || '').trim(),
                            ariaLabel: moneyEl?.getAttribute('aria-label') || '',
                        };
                    });
                }""",
                ML_MAX_CARDS_TO_SCAN,
            )
        except Exception as e:
            logger.debug("ML DOM bulk extraction failed", error=str(e))
            return []

        if not raw_cards:
            return []

        results: list[PartResult] = []
        exact_priced = 0
        for card in raw_cards:
            title = str(card.get("title") or "").strip()
            product_url = str(card.get("url") or "").strip()
            card_text = str(card.get("cardText") or "").strip()
            price = self._parse_card_price(
                str(card.get("fraction") or ""),
                str(card.get("cents") or ""),
                str(card.get("ariaLabel") or ""),
                card_text,
            )
            condition = self._detect_condition_from_text(f"{title} {card_text}")
            exact_match = self._contains_sku_evidence(
                searched_sku,
                title,
                card_text,
                product_url,
            )
            if price <= 0:
                continue
            results.append(
                PartResult(
                    sku_searched=searched_sku,
                    sku_found=searched_sku if exact_match else "",
                    exact_match=exact_match,
                    site=self.site_id,
                    site_name=self.site_name,
                    price=price,
                    currency=Currency.BRL,
                    condition=condition,
                    availability="Disponível",
                    seller_name="",
                    product_url=product_url,
                    origin="Brasil",
                    raw_title=title,
                )
            )
            if exact_match:
                exact_priced += 1

        if results:
            logger.debug(
                "ML DOM bulk extraction",
                sku=searched_sku,
                cards=len(raw_cards),
                priced=len(results),
                exact_priced=exact_priced,
            )
        return results

    @classmethod
    def _parse_card_price(
        cls,
        fraction: str,
        cents: str,
        aria_label: str,
        card_text: str,
    ) -> float:
        """Parse BRL price from andes-money-amount parts, aria-label, or card text."""
        price = 0.0
        if fraction:
            price_int = fraction.strip().replace(".", "")
            with contextlib.suppress(ValueError):
                price = float(price_int)
            if cents:
                cents_clean = re.sub(r"[^\d]", "", cents.strip())
                if cents_clean:
                    with contextlib.suppress(ValueError):
                        price += float(cents_clean) / 100

        if price <= 0 and aria_label:
            match = re.search(
                r"([\d]{1,3}(?:\.\d{3})*|\d+)\s*reais",
                aria_label,
                re.I,
            )
            if match:
                with contextlib.suppress(ValueError):
                    price = float(match.group(1).replace(".", ""))

        if price <= 0 and card_text:
            parsed = cls.parse_brazilian_price(card_text)
            if parsed is not None:
                price = parsed

        return price

    @staticmethod
    def _detect_condition_from_text(text: str) -> ItemCondition:
        lowered = (text or "").lower()
        if "usado" in lowered:
            return ItemCondition.USED
        if "novo" in lowered:
            return ItemCondition.NEW
        return ItemCondition.UNKNOWN

    async def _find_result_cards(self, page: Page):
        """Find product listing cards in ML search results."""
        selectors = [
            # ML search result items
            "li.ui-search-layout__item",
            "div.ui-search-result",
            # Newer ML layout
            "div.ui-search-result__wrapper",
            "div.andes-card.ui-search-result",
            # Poly layout
            "li.poly-card",
            "div.poly-component__body",
            # Generic fallback
            "ol.ui-search-layout li",
        ]
        for selector in selectors:
            cards = await page.query_selector_all(selector)
            if cards:
                logger.debug("ML: found result cards", selector=selector, count=len(cards))
                return cards
        return []

    async def _extract_card_result(self, card, searched_sku: str) -> PartResult | None:
        """Extract product data from a single ML search result card."""
        try:
            card_text = ""
            with contextlib.suppress(Exception):
                card_text = (await card.inner_text()).strip()

            # Title
            title_el = await card.query_selector(
                "h2.ui-search-item__title, "
                "a.ui-search-link__title-card, "
                "a.ui-search-item__group__element, "
                "h2.poly-component__title, "
                "a[class*='title']"
            )
            raw_title = ""
            if title_el:
                raw_title = (await title_el.inner_text()).strip()

            # Product URL
            link_el = await card.query_selector(
                "a.ui-search-link, "
                "a.ui-search-item__group__element, "
                "a.poly-component__title, "
                "a[href*='MLB']"
            )
            product_url = ""
            if link_el:
                href = await link_el.get_attribute("href")
                if href:
                    product_url = href

            fraction = ""
            cents = ""
            aria_label = ""
            price_int_el = await card.query_selector(
                "span.andes-money-amount__fraction, "
                "span.price-tag-fraction"
            )
            if price_int_el:
                fraction = (await price_int_el.inner_text()).strip()
            price_cents_el = await card.query_selector(
                "span.andes-money-amount__cents, "
                "span.price-tag-cents"
            )
            if price_cents_el:
                cents = (await price_cents_el.inner_text()).strip()
            money_el = await card.query_selector(
                ".andes-money-amount[aria-label], .andes-money-amount"
            )
            if money_el:
                aria_label = (await money_el.get_attribute("aria-label")) or ""

            price = self._parse_card_price(fraction, cents, aria_label, card_text)

            condition = ItemCondition.UNKNOWN
            condition_el = await card.query_selector(
                "span.ui-search-item__group__element--details, "
                "span[class*='condition'], "
                "span.poly-component__sold-count"
            )
            if condition_el:
                cond_text = (await condition_el.inner_text()).strip()
                condition = self._detect_condition_from_text(cond_text)
            else:
                condition = self._detect_condition_from_text(card_text)

            # Seller
            seller_el = await card.query_selector(
                "span.ui-search-official-store-label, "
                "p.ui-search-official-store-item__brand, "
                "span[class*='seller']"
            )
            seller_name = ""
            if seller_el:
                seller_name = (await seller_el.inner_text()).strip()

            exact_match = self._contains_sku_evidence(
                searched_sku,
                raw_title,
                card_text,
                product_url,
            )
            sku_found = searched_sku if exact_match else ""

            return PartResult(
                sku_searched=searched_sku,
                sku_found=sku_found,
                exact_match=exact_match,
                site=self.site_id,
                site_name=self.site_name,
                price=price,
                currency=Currency.BRL,
                condition=condition,
                availability="Disponível" if price > 0 else "unknown",
                seller_name=seller_name,
                product_url=product_url,
                origin="Brasil",
                raw_title=raw_title,
            )

        except Exception as e:
            logger.warning("ML card extraction error", error=str(e))
            return None

    async def _extract_single_product(self, page: Page, searched_sku: str) -> PartResult | None:
        """Extract data from a single ML product detail page."""
        try:
            # Title
            title_el = await page.query_selector("h1.ui-pdp-title")
            raw_title = ""
            if title_el:
                raw_title = (await title_el.inner_text()).strip()

            # Price
            price = 0.0
            price_el = await page.query_selector("span.andes-money-amount__fraction")
            if price_el:
                price_text = (await price_el.inner_text()).strip().replace(".", "")
                with contextlib.suppress(ValueError):
                    price = float(price_text)

            # Condition
            condition = ItemCondition.UNKNOWN
            condition_el = await page.query_selector("span.ui-pdp-subtitle")
            if condition_el:
                cond_text = (await condition_el.inner_text()).strip().lower()
                if "novo" in cond_text:
                    condition = ItemCondition.NEW
                elif "usado" in cond_text:
                    condition = ItemCondition.USED

            # Seller
            seller_el = await page.query_selector(
                "span.ui-pdp-action__info, "
                "a.ui-pdp-action__link"
            )
            seller_name = ""
            if seller_el:
                seller_name = (await seller_el.inner_text()).strip()

            page_text = ""
            with contextlib.suppress(Exception):
                page_text = await page.inner_text("body")

            return PartResult(
                sku_searched=searched_sku,
                sku_found=searched_sku,
                exact_match=self._contains_sku_evidence(
                    searched_sku,
                    raw_title,
                    page_text,
                    page.url,
                ),
                site=self.site_id,
                site_name=self.site_name,
                price=price,
                currency=Currency.BRL,
                condition=condition,
                availability="Disponível" if price > 0 else "unknown",
                seller_name=seller_name,
                product_url=page.url,
                origin="Brasil",
                raw_title=raw_title,
            )

        except Exception as e:
            logger.warning("ML single product extraction error", error=str(e))
            return None

    def _filter_new_only(self, results: list[PartResult]) -> list[PartResult]:
        """Remove used items — only return NEW parts per business requirement."""
        return [r for r in results if r.condition != ItemCondition.USED]

    @staticmethod
    def _compact_sku_text(value: str) -> str:
        """Normalize SKU evidence while preserving alphanumeric boundaries."""
        return re.sub(r"[^A-Za-z0-9]", "", unquote(value or "")).upper()

    @classmethod
    def _contains_sku_evidence(cls, searched_sku: str, *values: str) -> bool:
        """Return true when exact SKU evidence appears in title, card text, or URL."""
        compact_sku = cls._compact_sku_text(searched_sku)
        if not compact_sku:
            return False
        flexible_sku = r"[\s\-./_]*".join(re.escape(char) for char in compact_sku)
        sku_pattern = re.compile(rf"(?<![A-Z0-9]){flexible_sku}(?![A-Z0-9])")
        return any(bool(sku_pattern.search(unquote(value or "").upper())) for value in values)

    async def _verify_candidate_detail_pages(
        self,
        page: Page,
        results: list[PartResult],
        searched_sku: str,
    ) -> None:
        """Open ambiguous ML listings and confirm SKU evidence in product details."""
        checked = 0
        for result in results:
            if result.exact_match or not result.product_url or not result.price:
                continue
            if checked >= ML_DETAIL_CHECK_LIMIT:
                break

            checked += 1
            try:
                await self._wait_for_micro_interaction(600, 1600)
                logger.debug(
                    "ML detail verification: navigating",
                    sku=searched_sku,
                    url=result.product_url[:160],
                )
                await page.goto(result.product_url, wait_until="domcontentloaded", timeout=30000)
                await self._wait_for_page_settle(1200, 2600)
                if await self._check_blocked(page):
                    logger.warning("ML detail verification: blocked", sku=searched_sku)
                    return

                body_text = await page.inner_text("body")
                if self._contains_sku_evidence(searched_sku, body_text, page.url):
                    result.exact_match = True
                    result.sku_found = searched_sku
                    result.product_url = page.url
                    logger.debug(
                        "ML detail verification: exact match confirmed",
                        sku=searched_sku,
                        url=page.url[:160],
                    )
            except Exception as e:
                logger.debug(
                    "ML detail verification failed",
                    sku=searched_sku,
                    url=result.product_url[:160],
                    error=str(e),
                )
