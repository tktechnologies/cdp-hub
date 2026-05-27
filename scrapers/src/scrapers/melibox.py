"""Melibox/Sellerbox scraper — app.melibox.com.br.

Melibox is an authenticated Sellerbox portal for Mercado Livre sellers. The
scraper logs in, opens the **advProductPosition** workspace, searches via the
**Frase/Palavra** field (SKU), submits with **Enviar**, and reads prices from the
results table.
"""

import asyncio
import contextlib
import random
import re
from typing import Any
from urllib.parse import urljoin, urlparse

import structlog
from playwright.async_api import Locator, Page

from src.config import settings
from src.models.schemas import Currency, ItemCondition, PartResult, SiteId, SiteResult
from src.scrapers.base import BaseScraper

logger = structlog.get_logger()

BASE_URL = "https://app.melibox.com.br"
ADV_PATH = "/advProductPosition"

# Inputs tied to the advProductPosition "Frase/Palavra" filter (order: most specific first).
_PHRASE_INPUT_SELECTORS: tuple[str, ...] = (
    "#textoPesquisa",
    "input[name='textoPesquisa']",
    "#advProductPosition input[placeholder*='Frase' i]",
    "#advProductPosition input[placeholder*='Palavra' i]",
    "#advProductPosition input[name*='frase' i]",
    "#advProductPosition input[name*='palavra' i]",
    "#advProductPosition input[name*='phrase' i]",
    "#advProductPosition input[type='search']",
    "#advProductPosition input[type='text']",
    "[id*='advProductPosition' i] input[placeholder*='Frase' i]",
    "[id*='advProductPosition' i] input[placeholder*='Palavra' i]",
    "[id*='advProductPosition' i] input[type='search']",
    "[id*='advProductPosition' i] input[type='text']",
    "input[aria-label*='Frase' i]",
    "input[aria-label*='Palavra' i]",
)


class MeliboxScraper(BaseScraper):
    """Scraper for the authenticated Melibox/Sellerbox portal."""

    def __init__(self) -> None:
        super().__init__()
        self._last_login_blocked = False

    @property
    def site_id(self) -> SiteId:
        return SiteId.MELIBOX

    @property
    def site_name(self) -> str:
        return "Melibox Sellerbox"

    @property
    def base_url(self) -> str:
        return self._credentials.get("url") or BASE_URL

    def _login_url(self) -> str:
        """URL for the login entry page, even when credentials point to a work page."""
        configured = (self._credentials.get("url") or "").strip()
        if not configured:
            return BASE_URL

        if "advproductposition" not in configured.lower():
            return configured

        parsed = urlparse(configured)
        if parsed.scheme and parsed.netloc:
            return f"{parsed.scheme}://{parsed.netloc}"
        return BASE_URL

    def _work_page_url(self) -> str:
        """URL for the product-position screen (Frase/Palavra + Enviar)."""
        configured = (self._credentials.get("url") or "").strip()
        if "advproductposition" in configured.lower():
            return configured
        base = configured or BASE_URL
        parsed = urlparse(base)
        origin = (
            f"{parsed.scheme}://{parsed.netloc}" if parsed.scheme and parsed.netloc else BASE_URL
        )
        return urljoin(origin.rstrip("/") + "/", ADV_PATH.lstrip("/"))

    async def scrape_sku(self, sku: str, brand: str = "") -> SiteResult:
        """Run one SKU while reusing the logged-in browser context by default."""
        if (
            settings.proxy_rotation_enabled
            and settings.melibox_rotate_context_per_sku
            and self._context is not None
        ):
            logger.info("Melibox: rotating browser context before SKU", sku=sku)
            await self.shutdown()
            self._playwright = None
            self._browser = None
            self._context = None

        result = await super().scrape_sku(sku, brand)
        if (
            result.status == "error"
            and result.error_message == "Authentication failed"
            and self._last_login_blocked
        ):
            return SiteResult(
                site=self.site_id,
                site_name=self.site_name,
                status="blocked",
                error_message="Melibox login entry returned 403/access block",
                search_time_ms=result.search_time_ms,
            )
        return result

    async def login(self, page: Page) -> bool:
        """Log in to Melibox using configured credentials."""
        self._last_login_blocked = False
        username = self._credentials.get("username", "")
        password = self._credentials.get("password", "")
        if not username or not password:
            logger.warning("Melibox credentials are not configured")
            return False

        await page.goto(self._login_url(), wait_until="domcontentloaded", timeout=30000)
        await self._action_delay(900, 1800)

        if await self._detect_blocked(page):
            self._last_login_blocked = True
            logger.warning("Melibox login entry is blocked; clearing stored session and retrying")
            await self._clear_stored_session(page)
            await page.goto(self._login_url(), wait_until="domcontentloaded", timeout=30000)
            await self._action_delay(900, 1800)

        user_input = await self._first_visible(
            page,
            (
                'input[type="email"]',
                'input[name*="email" i]',
                'input[name*="user" i]',
                'input[placeholder*="email" i]',
                'input[placeholder*="usu" i]',
                'input[type="text"]',
            ),
        )
        pass_input = await self._first_visible(
            page,
            (
                'input[type="password"]',
                'input[name*="senha" i]',
                'input[placeholder*="senha" i]',
            ),
        )
        if user_input is None or pass_input is None:
            logger.warning("Melibox login form missing; clearing stored session and retrying once")
            await self._clear_stored_session(page)
            await page.goto(self._login_url(), wait_until="domcontentloaded", timeout=30000)
            await self._action_delay(900, 1800)
            user_input = await self._first_visible(
                page,
                (
                    'input[type="email"]',
                    'input[name*="email" i]',
                    'input[name*="user" i]',
                    'input[placeholder*="email" i]',
                    'input[placeholder*="usu" i]',
                    'input[type="text"]',
                ),
            )
            pass_input = await self._first_visible(
                page,
                (
                    'input[type="password"]',
                    'input[name*="senha" i]',
                    'input[placeholder*="senha" i]',
                ),
            )

        if user_input is None or pass_input is None:
            if await self._detect_blocked(page):
                self._last_login_blocked = True
            logger.warning("Melibox login form was not visible")
            return False

        await user_input.click()
        await self._action_delay(250, 700)
        await user_input.fill(username)
        await self._action_delay(400, 900)
        await pass_input.click()
        await self._action_delay(250, 700)
        await pass_input.fill(password)
        await self._action_delay(500, 1200)

        submit = (
            page.locator("button, input[type='submit']")
            .filter(has_text=re.compile(r"entrar|login|acessar|continuar", re.I))
            .first
        )
        if await submit.count() and await submit.is_visible():
            await submit.click()
        else:
            await page.keyboard.press("Enter")

        await page.wait_for_load_state("domcontentloaded", timeout=30000)
        await self._action_delay(1500, 3000)
        return await self._is_session_valid(page)

    async def _clear_stored_session(self, page: Page) -> None:
        """Drop stale Melibox cookies/state before a fresh login attempt."""
        with contextlib.suppress(FileNotFoundError):
            self.state_file.unlink()
        with contextlib.suppress(Exception):
            await page.context.clear_cookies()
        with contextlib.suppress(Exception):
            await page.evaluate("localStorage.clear(); sessionStorage.clear();")

    async def _is_session_valid(self, page: Page) -> bool:
        """Open the work page once; a visible password field means the session expired."""
        if not self._credentials.get("username") or not self._credentials.get("password"):
            return False

        try:
            await page.goto(self._work_page_url(), wait_until="domcontentloaded", timeout=30000)
            await self._action_delay(500, 1200)
            password_inputs = page.locator('input[type="password"]')
            for index in range(await password_inputs.count()):
                if await password_inputs.nth(index).is_visible():
                    return False
            return not await self._detect_blocked(page)
        except Exception:
            return False

    async def _detect_blocked(self, page: Page) -> bool:
        """Detect only visible Melibox access challenges.

        Melibox can keep hidden recaptcha/challenge markup on normal app pages.
        The shared detector treats any CAPTCHA iframe as blocked, which can be
        too aggressive here. For this authenticated app, only visible challenge
        UI or clear page text should stop the run.
        """
        try:
            body_text = (await page.inner_text("body")).lower()
        except Exception:
            body_text = ""

        visible_text_indicators = [
            "access denied",
            "acesso negado",
            "403 forbidden",
            "429 too many requests",
            "you have been blocked",
            "please verify you are a human",
            "verify you are human",
            "verifique que você é humano",
            "checking your browser",
            "just a moment",
        ]
        for indicator in visible_text_indicators:
            if indicator in body_text:
                logger.warning("Melibox visible block text detected", indicator=indicator)
                return True

        visible_challenge_selectors = (
            "#challenge-running",
            "#challenge-form",
            "iframe[src*='captcha']",
            "iframe[src*='challenge']",
            "iframe[src*='turnstile']",
            "input[name='cf-turnstile-response']",
            "div.cf-browser-verification",
            "div[class*='captcha']",
        )
        for selector in visible_challenge_selectors:
            locator = page.locator(selector)
            for index in range(await locator.count()):
                try:
                    if await locator.nth(index).is_visible():
                        logger.warning(
                            "Melibox visible challenge element detected", selector=selector
                        )
                        return True
                except Exception:
                    continue

        return False

    async def search_sku(self, page: Page, sku: str, brand: str = "") -> list[PartResult]:
        """Open advProductPosition, search SKU in Frase/Palavra, submit Enviar, parse rows."""
        await self._sku_delay(sku)

        work_url = self._work_page_url()
        if "advproductposition" not in page.url.lower():
            logger.info("Melibox: loading product position page", sku=sku, url=work_url)
            await page.goto(work_url, wait_until="domcontentloaded", timeout=30000)
            await self._action_delay(800, 1600)
        if await self._detect_blocked(page):
            return []

        phrase = await self._resolve_phrase_input(page)
        if phrase is None:
            logger.warning("Melibox: Frase/Palavra input not found", sku=sku)
            return []

        await phrase.click()
        await self._action_delay(200, 500)
        await phrase.fill(sku)
        await self._action_delay(400, 900)

        submitted = await self._click_enviar(page)
        if not submitted:
            logger.info("Melibox: Enviar not found; pressing Enter on phrase field", sku=sku)
            await phrase.press("Enter")

        await self._action_delay(1200, 2400)
        with contextlib.suppress(Exception):
            await page.wait_for_load_state("networkidle", timeout=20000)
        with contextlib.suppress(Exception):
            await page.wait_for_load_state("domcontentloaded", timeout=8000)

        await self._wait_for_results_skeleton(page)
        rows = await self._extract_adv_product_rows(page, sku)
        if not rows:
            logger.warning(
                "Melibox: no table rows matched this SKU after Enviar — "
                "verify inventory, Frase/Palavra field, or table selectors",
                sku=sku,
            )
        return rows

    async def _resolve_phrase_input(self, page: Page) -> Locator | None:
        role = page.get_by_role("textbox", name=re.compile(r"frase|palavra", re.I))
        try:
            if await role.count() > 0:
                first = role.first
                await first.wait_for(state="visible", timeout=10000)
                return first
        except Exception:
            pass

        return await self._first_visible(page, _PHRASE_INPUT_SELECTORS)

    async def _click_enviar(self, page: Page) -> bool:
        """Click the Enviar control scoped to advProductPosition when possible."""
        scopes = (
            page.locator("#advProductPosition"),
            page.locator("[id*='advProductPosition' i]"),
            page.locator("body"),
        )
        for scope in scopes:
            if await scope.count() == 0:
                continue
            root = scope.first
            for locator in (
                root.get_by_role("button", name=re.compile(r"^enviar$", re.I)),
                root.get_by_role("button", name=re.compile(r"enviar", re.I)),
                root.locator("button:has-text('Enviar')"),
                root.locator("input[type='submit'][value*='Enviar' i]"),
            ):
                try:
                    if await locator.count() == 0:
                        continue
                    target = locator.first
                    if await target.is_visible():
                        await target.click(timeout=8000)
                        return True
                except Exception:
                    continue
        return False

    async def _wait_for_results_skeleton(self, page: Page) -> None:
        """Best-effort wait for listing rows after submit (SPA or full navigation)."""
        row = page.locator(
            "#advProductPosition table tbody tr, "
            "[id*='advProductPosition' i] table tbody tr, "
            "main table tbody tr, "
            "table tbody tr"
        ).first
        try:
            await row.wait_for(state="visible", timeout=25000)
        except Exception:
            logger.info("Melibox: no table row became visible within timeout")

    async def _extract_adv_product_rows(self, page: Page, searched_sku: str) -> list[PartResult]:
        """Parse table/grid rows under advProductPosition (or main fallback)."""
        root = page.locator("#advProductPosition, [id*='ProductPosition' i]").first
        if await root.count() == 0 or not await root.is_visible():
            root = (
                page.locator("main").first
                if await page.locator("main").count()
                else page.locator("body")
            )

        row_locator = root.locator("table tbody tr, [role='rowgroup'] [role='row']")
        n = await row_locator.count()
        logger.info("Melibox: candidate table rows", sku=searched_sku, row_count=n)

        results: list[PartResult] = []

        for i in range(n):
            row = row_locator.nth(i)
            try:
                if not await row.is_visible():
                    continue
            except Exception:
                continue

            th_only = await row.locator("th").count()
            td_count = await row.locator("td").count()
            if th_only > 0 and td_count == 0:
                continue

            cell_texts: list[str] = []
            try:
                cell_texts = [
                    re.sub(r"\s+", " ", cell).strip()
                    for cell in await row.locator(
                        "td, [role='cell'], [role='gridcell']"
                    ).all_inner_texts()
                ]
            except Exception:
                cell_texts = []

            try:
                text = (await row.inner_text()).strip()
            except Exception:
                continue
            compact = re.sub(r"\s+", " ", text)
            if len(compact) < 4:
                continue

            href = ""
            try:
                links = row.locator("a[href]")
                if await links.count() > 0:
                    href = (await links.first.get_attribute("href")) or ""
            except Exception:
                href = ""

            product_url = self._absolute_url(href) if href else str(page.url)
            sku_haystack = f"{compact} {href} {product_url}"
            if not self._contains_sku(sku_haystack, searched_sku):
                continue

            price_token = self._price_token_from_cells_or_text(cell_texts, compact)
            exact = self._contains_sku(sku_haystack, searched_sku)
            condition = ItemCondition.UNKNOWN
            if re.search(r"\bnovo\b|\bnew\b", compact, re.I):
                condition = ItemCondition.NEW
            elif re.search(r"\busado\b|\bused\b", compact, re.I):
                condition = ItemCondition.USED

            availability = "unknown"
            if re.search(r"pausado|inativ|indispon", compact, re.I):
                availability = "unavailable"
            elif re.search(r"ativo|dispon", compact, re.I):
                availability = "available"

            title = compact[:240]
            results.append(
                PartResult(
                    sku_searched=searched_sku,
                    sku_found=searched_sku if exact else self._extract_candidate_sku(compact),
                    exact_match=exact,
                    site=self.site_id,
                    site_name=self.site_name,
                    price=self._parse_price(price_token) if price_token else None,
                    currency=Currency.BRL,
                    condition=condition,
                    availability=availability,
                    seller_name="Melibox",
                    product_url=product_url,
                    origin="Brasil",
                    raw_title=title,
                )
            )
            if len(results) >= 25:
                break

        logger.info(
            "Melibox: extracted rows from product position", sku=searched_sku, count=len(results)
        )
        return results

    @staticmethod
    def _first_brl_price_token(text: str) -> str:
        match = re.search(r"R\$\s*([\d]{1,3}(?:\.\d{3})*,\d{2}|\d+(?:[.,]\d+)?)", text, re.I)
        return match.group(1) if match else ""

    @classmethod
    def _price_token_from_cells_or_text(cls, cell_texts: list[str], text: str) -> str:
        """Return Melibox's product price token.

        The advProductPosition table labels the price column as ``R$`` but the
        data cells contain only Brazilian-formatted amounts like ``568,83``.
        """
        for index in (5,):
            if index < len(cell_texts):
                token = cls._plain_brazilian_price_token(cell_texts[index])
                if token:
                    return token

        brl_token = cls._first_brl_price_token(text)
        if brl_token:
            return brl_token

        for cell in cell_texts:
            token = cls._plain_brazilian_price_token(cell)
            if token:
                return token
        return ""

    @staticmethod
    def _plain_brazilian_price_token(text: str) -> str:
        match = re.search(r"(?<![\d])(\d{1,3}(?:\.\d{3})*,\d{2}|\d{2,6},\d{2})(?![\d])", text)
        return match.group(1) if match else ""

    async def _sku_delay(self, sku: str) -> None:
        min_delay = max(settings.melibox_sku_delay_min, 0.0)
        max_delay = max(settings.melibox_sku_delay_max, min_delay)
        if max_delay <= 0:
            return
        delay = random.uniform(min_delay, max_delay)
        logger.info("Melibox: pacing before SKU search", sku=sku, delay_s=round(delay, 2))
        await asyncio.sleep(delay)

    async def _first_visible(self, page: Page, selectors: tuple[str, ...]) -> Any | None:
        for selector in selectors:
            locator = page.locator(selector)
            for index in range(await locator.count()):
                candidate = locator.nth(index)
                if await candidate.is_visible():
                    return candidate
        return None

    def _absolute_url(self, href: str) -> str:
        if href.startswith("http"):
            return href
        origin = urlparse(self._work_page_url())
        base_origin = (
            f"{origin.scheme}://{origin.netloc}" if origin.scheme and origin.netloc else BASE_URL
        )
        return urljoin(base_origin + "/", href.lstrip("/"))

    @staticmethod
    def _parse_price(price_text: str) -> float | None:
        return BaseScraper.parse_brazilian_price(price_text)

    @staticmethod
    def _contains_sku(text: str, searched_sku: str) -> bool:
        return BaseScraper.contains_sku(text, searched_sku)

    @staticmethod
    def _extract_candidate_sku(text: str) -> str:
        for match in re.finditer(r"\b[A-Z0-9][A-Z0-9.\-/]{4,24}\b", text.upper()):
            candidate = match.group(0)
            if any(char.isdigit() for char in candidate):
                return candidate
        return ""
