"""Base scraper with session management, authentication, retry logic, and anti-bot detection."""

import asyncio
import contextlib
import random
import re
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import structlog
from playwright.async_api import Browser, BrowserContext, Page, Playwright, async_playwright
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from src.config import settings
from src.models.schemas import PartResult, SiteId, SiteResult
from src.utils.anti_bot_guard import anti_bot_circuit_breaker
from src.utils.monitoring import record_scrape_result
from src.utils.proxy_manager import ProxyEndpoint, get_proxy_manager

logger = structlog.get_logger()


class BaseScraper(ABC):
    """Abstract base class for all site scrapers.

    Subclasses MUST implement:
        - site_id: SiteId property
        - site_name: str property
        - login(page) -> bool
        - search_sku(page, sku, brand) -> list[PartResult]

    The base class handles:
        - Browser/context lifecycle
        - Session state persistence (storageState)
        - Session validation and re-authentication
        - Error handling, screenshots, and logging
        - Timing and metrics
    """

    def __init__(self) -> None:
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._credentials: dict[str, str] = {}
        self._last_http_block: dict[str, int | str] | None = None
        self._session_confirmed_at: float | None = None
        self._proxy_endpoint: ProxyEndpoint | None = None
        self._proxy_identity: str | None = None

    # ─── Abstract Properties ──────────────────────────────────────

    @property
    @abstractmethod
    def site_id(self) -> SiteId:
        """Unique site identifier."""
        ...

    @property
    @abstractmethod
    def site_name(self) -> str:
        """Human-readable site name (e.g., 'GM Parts Dealer')."""
        ...

    @property
    def state_file(self) -> Path:
        """Path to persisted browser state for this site."""
        state_dir = settings.browser_state_dir
        state_dir.mkdir(parents=True, exist_ok=True)
        if (
            settings.proxy_rotation_enabled
            and settings.proxy_state_per_identity
            and self._proxy_identity
        ):
            return state_dir / f"{self.site_id.value}_{self._proxy_identity}_state.json"
        return state_dir / f"{self.site_id.value}_state.json"

    @property
    def base_url(self) -> str:
        """Base URL for this site from credentials config."""
        return self._credentials.get("url", "")

    # ─── Abstract Methods ─────────────────────────────────────────

    @abstractmethod
    async def login(self, page: Page) -> bool:
        """Perform login on the site. Return True if successful.

        Implementations should:
        1. Navigate to login page
        2. Fill username/password
        3. Click submit
        4. Verify login succeeded (check for dashboard element, etc.)
        """
        ...

    @abstractmethod
    async def search_sku(self, page: Page, sku: str, brand: str = "") -> list[PartResult]:
        """Search for a SKU on this site and extract results.

        Args:
            page: Authenticated Playwright page
            sku: The SKU code to search (already normalized)
            brand: Optional brand for brand-specific logic (e.g., Mercedes)

        Returns:
            List of PartResult for all matching items found
        """
        ...

    # ─── Lifecycle ────────────────────────────────────────────────

    async def initialize(self) -> None:
        """Start browser and create context with stored session if available."""
        self._credentials = settings.get_site_credentials(self.site_id.value)
        proxy = get_proxy_manager().proxy_for_site(self.site_id.value)
        self._proxy_endpoint = proxy
        self._proxy_identity = proxy.identity if proxy else None

        self._playwright = await async_playwright().start()
        playwright = self._playwright
        launch_opts: dict[str, Any] = {
            "headless": settings.playwright_headless,
            "args": ["--disable-blink-features=AutomationControlled"],
        }
        if settings.playwright_slow_mo_ms > 0:
            launch_opts["slow_mo"] = settings.playwright_slow_mo_ms

        self._browser = await playwright.chromium.launch(**launch_opts)

        # Restore session state if it exists
        raw_browser_version = getattr(self._browser, "version", "")
        browser_version = raw_browser_version() if callable(raw_browser_version) else raw_browser_version
        browser_version = str(browser_version or "")
        context_opts = self._build_context_options(browser_version)
        if self.state_file.exists():
            context_opts["storage_state"] = str(self.state_file)
            logger.info("Restoring session state", site=self.site_id.value)

        if proxy:
            context_opts["proxy"] = proxy.to_playwright()
            logger.info(
                "Using outbound proxy",
                site=self.site_id.value,
                proxy=proxy.server,
                proxy_identity=proxy.identity,
            )

        self._context = await self._browser.new_context(**context_opts)
        await self._install_anti_bot_context()

    def _httpx_proxy_url(self) -> str | None:
        """Return the current proxy URL for source-specific HTTP preflights."""
        if not self._proxy_endpoint:
            return None
        return self._proxy_endpoint.to_httpx_url()

    def _select_user_agent(self, browser_version: str = "") -> str:
        """Choose a Chromium-compatible user agent for this browser context."""
        configured_agents = [
            user_agent.strip()
            for user_agent in settings.browser_user_agents
            if user_agent.strip()
        ]
        if configured_agents:
            return random.choice(configured_agents)

        major_version = (browser_version or "").split(".", maxsplit=1)[0]
        if not major_version.isdigit():
            major_version = "131"
        return (
            "Mozilla/5.0 (X11; Linux x86_64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            f"Chrome/{major_version}.0.0.0 Safari/537.36"
        )

    def _extra_http_headers(self) -> dict[str, str]:
        """Headers that complement Playwright's real Chromium request headers."""
        if not settings.browser_extra_http_headers_enabled:
            return {}

        headers: dict[str, str] = {}
        if settings.browser_accept_language:
            headers["Accept-Language"] = settings.browser_accept_language
        return headers

    def _build_context_options(self, browser_version: str = "") -> dict[str, Any]:
        """Build a realistic browser context profile shared by all scrapers."""
        viewport = {
            "width": settings.browser_viewport_width,
            "height": settings.browser_viewport_height,
        }
        context_opts: dict[str, Any] = {
            "viewport": viewport,
            "screen": viewport,
            "locale": settings.browser_locale,
            "timezone_id": settings.browser_timezone_id,
            "user_agent": self._select_user_agent(browser_version),
        }

        extra_headers = self._extra_http_headers()
        if extra_headers:
            context_opts["extra_http_headers"] = extra_headers

        return context_opts

    async def _install_anti_bot_context(self) -> None:
        """Install low-risk browser context hardening."""
        if not self._context or not settings.browser_stealth_enabled:
            return

        await self._context.add_init_script(
            """
(() => {
  Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
  window.chrome = window.chrome || {};
  window.chrome.runtime = window.chrome.runtime || {};
})();
"""
        )

    async def _new_page(self) -> Page:
        """Create a page and attach anti-bot response observers."""
        assert self._context is not None
        page = await self._context.new_page()
        self._attach_anti_bot_observers(page)
        return page

    def _attach_anti_bot_observers(self, page: Page) -> None:
        """Track main-document 403/429 responses as anti-bot blocks."""

        def record_response(response: Any) -> None:
            status = int(getattr(response, "status", 0) or 0)
            if status not in settings.anti_bot_block_status_codes:
                return

            request = getattr(response, "request", None)
            is_navigation = False
            resource_type = ""
            if request is not None:
                with contextlib.suppress(Exception):
                    is_navigation = bool(request.is_navigation_request())
                resource_type = str(getattr(request, "resource_type", "") or "")

            if not is_navigation and resource_type != "document":
                return

            url = str(getattr(response, "url", "") or "")
            self._last_http_block = {"status": status, "url": url}
            logger.warning(
                "HTTP block response detected",
                site=self.site_id.value,
                status=status,
                url=url,
            )

        page.on("response", record_response)

    async def shutdown(self) -> None:
        """Save session state and close browser."""
        if self._context:
            try:
                await self._context.storage_state(path=str(self.state_file))
                logger.info("Session state saved", site=self.site_id.value)
            except Exception as e:
                logger.warning("Failed to save session state", site=self.site_id.value, error=str(e))
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

    # ─── Session Management ───────────────────────────────────────

    def _session_confirmed_within_recheck_window(self) -> bool:
        """True when a recent probe/login succeeded in this worker process."""
        if self._session_confirmed_at is None:
            return False
        elapsed = time.monotonic() - self._session_confirmed_at
        return elapsed < settings.session_recheck_seconds

    def _mark_session_confirmed(self) -> None:
        self._session_confirmed_at = time.monotonic()

    def _invalidate_session_cache(self) -> None:
        self._session_confirmed_at = None

    async def ensure_authenticated(self, page: Page) -> bool:
        """Check if current session is valid, re-login if needed."""
        if self._session_confirmed_within_recheck_window():
            logger.info("Session still valid", site=self.site_id.value)
            return True

        if await self._is_session_valid(page):
            self._mark_session_confirmed()
            logger.info("Session still valid", site=self.site_id.value)
            return True

        self._invalidate_session_cache()
        logger.info("Session expired, re-authenticating", site=self.site_id.value)
        success = await self.login(page)
        if success:
            assert self._context is not None
            await self._context.storage_state(path=str(self.state_file))
            self._mark_session_confirmed()
            logger.info("Re-authentication successful", site=self.site_id.value)
        else:
            logger.error("Re-authentication failed", site=self.site_id.value)
        return success

    async def _is_session_valid(self, page: Page) -> bool:
        """Check if the stored session is still authenticated.

        Default implementation navigates to base_url and checks for login form.
        Override in subclasses for site-specific validation.
        """
        try:
            await page.goto(self.base_url, wait_until="domcontentloaded", timeout=30000)
            # If we land on a page with a login form, session is expired
            login_form = await page.query_selector('input[type="password"]')
            return login_form is None
        except Exception:
            return False

    # ─── Public API ───────────────────────────────────────────────

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(min=2, max=30),
        retry=retry_if_exception_type((asyncio.TimeoutError, ConnectionError)),
        reraise=True
    )
    async def _search_with_retry(self, page: Page, sku: str, brand: str) -> list[PartResult]:
        """Execute search with retry logic for transient failures."""
        try:
            return await self.search_sku(page, sku, brand)
        except Exception as e:
            logger.warning(
                "Search attempt failed",
                site=self.site_id.value,
                sku=sku,
                error=str(e),
                error_type=type(e).__name__
            )
            raise

    async def scrape_sku(self, sku: str, brand: str = "") -> SiteResult:
        """Full scraping pipeline for a single SKU.

        Handles: initialization, authentication, search, error capture.
        """
        start_time = time.monotonic()
        page: Page | None = None

        try:
            if not self._context:
                await self.initialize()

            assert self._context is not None
            circuit_open, retry_after, reason = anti_bot_circuit_breaker.is_open(
                self.site_id.value,
                self._proxy_identity,
            )
            if circuit_open:
                result = self._blocked_site_result(
                    start_time,
                    (
                        "Anti-bot circuit breaker open"
                        f" for {retry_after}s after repeated blocks"
                        + (f": {reason}" if reason else "")
                    ),
                )
                record_scrape_result(
                    self.site_id.value,
                    result.status,
                    result.search_time_ms / 1000,
                    self._proxy_identity,
                )
                return result

            self._last_http_block = None
            page = await self._new_page()

            # Ensure we're logged in
            if not await self.ensure_authenticated(page):
                blocked_message = await self._blocking_message(page)
                if blocked_message:
                    result = self._blocked_site_result(
                        start_time,
                        blocked_message,
                    )
                    anti_bot_circuit_breaker.record_block(
                        self.site_id.value,
                        self._proxy_identity,
                        blocked_message,
                    )
                    record_scrape_result(
                        self.site_id.value,
                        result.status,
                        result.search_time_ms / 1000,
                        self._proxy_identity,
                    )
                    return result
                result = SiteResult(
                    site=self.site_id,
                    site_name=self.site_name,
                    status="error",
                    error_message="Authentication failed",
                    search_time_ms=int((time.monotonic() - start_time) * 1000),
                )
                record_scrape_result(
                    self.site_id.value,
                    result.status,
                    result.search_time_ms / 1000,
                    self._proxy_identity,
                )
                return result

            # Normalize SKU based on business rules
            normalized_sku = self._normalize_sku(sku, brand)

            # Execute search with retry logic
            max_attempts = max(1, settings.anti_bot_retry_attempts)
            results: list[PartResult] = []
            blocked_message = ""
            for attempt in range(max_attempts):
                self._last_http_block = None
                results = await self._search_with_retry(page, normalized_sku, brand)
                blocked_message = await self._blocking_message(page)
                if not blocked_message:
                    break

                elapsed_ms = int((time.monotonic() - start_time) * 1000)
                logger.warning(
                    "Blocked by anti-bot protection",
                    site=self.site_id.value,
                    sku=sku,
                    attempt=attempt + 1,
                    max_attempts=max_attempts,
                    elapsed_ms=elapsed_ms,
                )
                if attempt >= max_attempts - 1:
                    result = self._blocked_site_result(start_time, blocked_message)
                    anti_bot_circuit_breaker.record_block(
                        self.site_id.value,
                        self._proxy_identity,
                        blocked_message,
                    )
                    record_scrape_result(
                        self.site_id.value,
                        result.status,
                        result.search_time_ms / 1000,
                        self._proxy_identity,
                    )
                    return result

                await self._anti_bot_backoff(attempt)
                with contextlib.suppress(Exception):
                    await page.close()
                page = await self._new_page()

            # Filter exact matches
            exact_results = [r for r in results if r.exact_match]

            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            logger.info(
                "SKU search completed",
                site=self.site_id.value,
                sku=sku,
                results_count=len(results),
                exact_count=len(exact_results),
                elapsed_ms=elapsed_ms,
            )

            result = self._site_result_from_search(results, elapsed_ms)
            if result.status != "blocked":
                anti_bot_circuit_breaker.record_success(self.site_id.value, self._proxy_identity)
            record_scrape_result(
                self.site_id.value,
                result.status,
                result.search_time_ms / 1000,
                self._proxy_identity,
            )
            return result

        except Exception as e:
            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            logger.error(
                "Scrape failed",
                site=self.site_id.value, sku=sku, error=str(e), exc_info=True,
            )
            # Capture screenshot on error
            if page and settings.screenshot_on_error:
                try:
                    screenshot_path = settings.browser_state_dir / f"error_{self.site_id.value}_{sku}.png"
                    await page.screenshot(path=str(screenshot_path))
                except Exception:
                    pass

            result = SiteResult(
                site=self.site_id,
                site_name=self.site_name,
                status="error",
                error_message=str(e),
                search_time_ms=elapsed_ms,
            )
            record_scrape_result(
                self.site_id.value,
                result.status,
                result.search_time_ms / 1000,
                self._proxy_identity,
            )
            return result
        finally:
            if page:
                await page.close()

    async def _blocking_message(self, page: Page) -> str:
        """Return a blocked-status message when HTTP or page signals show a block."""
        if self._last_http_block:
            status = self._last_http_block.get("status", "")
            return f"HTTP {status} anti-bot or access restriction detected"

        if await self._detect_blocked(page):
            return "Anti-bot or access restriction detected"

        return ""

    def _blocked_site_result(self, start_time: float, error_message: str) -> SiteResult:
        """Build a shared blocked SiteResult with elapsed timing."""
        elapsed_ms = int((time.monotonic() - start_time) * 1000)
        return SiteResult(
            site=self.site_id,
            site_name=self.site_name,
            status="blocked",
            error_message=error_message,
            search_time_ms=elapsed_ms,
        )

    async def _anti_bot_backoff(self, attempt: int) -> None:
        """Bounded exponential backoff after 403/429/challenge detection."""
        minimum = max(0.0, settings.anti_bot_backoff_min_seconds)
        maximum = max(minimum, settings.anti_bot_backoff_max_seconds)
        base_wait = random.uniform(minimum, maximum)
        wait_seconds = base_wait * (2 ** attempt)
        logger.info(
            "Anti-bot backoff before retry",
            site=self.site_id.value,
            attempt=attempt + 1,
            wait_seconds=round(wait_seconds, 2),
        )
        await asyncio.sleep(wait_seconds)

    # ─── SKU Normalization ────────────────────────────────────────

    def _normalize_sku(self, sku: str, brand: str = "") -> str:
        """Apply business rules for SKU normalization.

        Rules:
        1. Strip whitespace and special characters (hyphens, dots, spaces)
        2. For Mercedes parts on European sites: remove first character
        """
        normalized = re.sub(r"[\s\-\.\/]", "", sku.strip()).upper()

        # Mercedes rule: remove first character for European site searches
        if (
            brand.lower() in ("mercedes", "mb", "mercedes-benz")
            and self.site_id == SiteId.EUROPE
            and len(normalized) > 1
        ):
            normalized = normalized[1:]
            logger.debug("Mercedes SKU adjusted for EU", original=sku, normalized=normalized)

        return normalized

    @staticmethod
    def validate_exact_match(searched_sku: str, found_sku: str) -> bool:
        """Check if found SKU exactly matches searched SKU (after normalization)."""
        clean_searched = re.sub(r"[\s\-\.\/]", "", searched_sku).upper()
        clean_found = re.sub(r"[\s\-\.\/]", "", found_sku).upper()
        return clean_searched == clean_found

    @staticmethod
    def contains_sku(text: str, searched_sku: str) -> bool:
        """Return true when a SKU appears in free text after light normalization."""
        clean_text = re.sub(r"[\s\-\.\/]", "", text or "").upper()
        clean_sku = re.sub(r"[\s\-\.\/]", "", searched_sku or "").upper()
        return bool(clean_sku and clean_sku in clean_text)

    @staticmethod
    def parse_brazilian_price(price_text: str) -> float | None:
        """Parse Brazilian price text such as R$ 1.234,56."""
        if not price_text:
            return None
        try:
            cleaned = re.sub(r"[^\d,.]", "", price_text)
            if not cleaned:
                return None
            cleaned = cleaned.replace(".", "").replace(",", ".")
            value = float(cleaned)
        except (TypeError, ValueError):
            return None
        return value if value > 0 else None

    @staticmethod
    def _is_out_of_stock(availability: str) -> bool:
        text = (availability or "").lower()
        return any(
            phrase in text
            for phrase in (
                "fora de estoque",
                "sem estoque",
                "esgotado",
                "indisponível",
                "indisponivel",
                "temporarily out",
                "out of stock",
                "unavailable",
                "pausado",
                "inativo",
            )
        )

    @classmethod
    def _is_priced_in_stock(cls, result: PartResult) -> bool:
        """Return true when an exact result has usable stock and price data."""
        return (
            result.exact_match
            and result.price is not None
            and result.price > 0
            and not cls._is_out_of_stock(result.availability)
        )

    def _site_result_from_search(
        self, results: list[PartResult], elapsed_ms: int
    ) -> SiteResult:
        """Classify scraper results while preserving exact out-of-stock evidence."""
        priced_results = [result for result in results if self._is_priced_in_stock(result)]
        if priced_results:
            return SiteResult(
                site=self.site_id,
                site_name=self.site_name,
                status="success",
                results=priced_results,
                search_time_ms=elapsed_ms,
            )

        exact_results = [result for result in results if result.exact_match]
        if exact_results:
            return SiteResult(
                site=self.site_id,
                site_name=self.site_name,
                status="no_price",
                results=exact_results,
                search_time_ms=elapsed_ms,
            )

        return SiteResult(
            site=self.site_id,
            site_name=self.site_name,
            status="not_found",
            results=[],
            search_time_ms=elapsed_ms,
        )

    async def _wait_for_page_settle(
        self, minimum_ms: int = 900, maximum_ms: int = 2200
    ) -> None:
        """Tunable settle wait after navigation or SPA updates."""
        await self._action_delay(minimum_ms, maximum_ms)

    async def _wait_for_post_submit(
        self, minimum_ms: int = 1200, maximum_ms: int = 3000
    ) -> None:
        """Tunable wait after submitting forms such as CEP or SKU search."""
        await self._action_delay(minimum_ms, maximum_ms)

    async def _wait_for_micro_interaction(
        self, minimum_ms: int = 200, maximum_ms: int = 700
    ) -> None:
        """Tunable wait between click/fill/key interactions."""
        await self._action_delay(minimum_ms, maximum_ms)

    async def _wait_for_results(
        self, page: Page, selector: str, timeout_ms: int = 8000
    ) -> None:
        """Wait for result selectors, then settle briefly; ignore absent optional results."""
        try:
            await page.wait_for_selector(selector, timeout=timeout_ms)
        except Exception:
            logger.debug("Result selector wait timed out", site=self.site_id.value)
        await self._wait_for_page_settle()

    async def _action_delay(self, minimum_ms: int | None = None, maximum_ms: int | None = None) -> None:
        """Small jittered in-page delay to avoid tight bot-like action loops."""
        min_ms = settings.scraper_action_delay_min_ms if minimum_ms is None else minimum_ms
        max_ms = settings.scraper_action_delay_max_ms if maximum_ms is None else maximum_ms
        if max_ms <= 0:
            return
        if min_ms < 0:
            min_ms = 0
        if max_ms < min_ms:
            max_ms = min_ms
        await asyncio.sleep(random.uniform(min_ms, max_ms) / 1000)

    # ─── Anti-Bot / Blocked Detection ─────────────────────────────

    async def _detect_blocked(self, page: Page) -> bool:
        """Check the current page for common anti-bot / access-denied indicators.

        Subclasses may override for site-specific detection.
        Returns True if the page appears blocked.
        """
        try:
            body_text = (await page.inner_text("body")).lower()
        except Exception:
            return False

        block_indicators = [
            "access denied",
            "acesso negado",
            "403 forbidden",
            "429 too many requests",
            "rate limit",
            "you have been blocked",
            "please verify you are a human",
            "verify you are human",
            "verifique que você é humano",
            "checking your browser",
            "attention required",
            "cloudflare",
            "turnstile",
            "just a moment",  # Cloudflare challenge
        ]
        for indicator in block_indicators:
            if indicator in body_text:
                logger.warning(
                    "Block indicator detected",
                    site=self.site_id.value,
                    indicator=indicator,
                )
                return True

        # Check for Cloudflare challenge div or CAPTCHA iframe
        cf_challenge = await page.query_selector(
            "#challenge-running, #challenge-form, "
            "iframe[src*='captcha'], iframe[src*='challenge'], "
            "iframe[src*='turnstile'], input[name='cf-turnstile-response'], "
            "div.cf-browser-verification, div[class*='captcha']"
        )
        if cf_challenge:
            logger.warning(
                "CAPTCHA/challenge element detected",
                site=self.site_id.value,
            )
            return True

        return False
