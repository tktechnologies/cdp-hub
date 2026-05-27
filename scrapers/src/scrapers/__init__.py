"""Scraper registry and session lifecycle management."""

import structlog

from src.config import settings
from src.models.schemas import SiteId
from src.scrapers.base import BaseScraper
from src.scrapers.ebay import EbayScraper
from src.scrapers.eu_imports import EUImportsScraper
from src.scrapers.gm import GMScraper
from src.scrapers.goparts import GoPartsScraper
from src.scrapers.melibox import MeliboxScraper
from src.scrapers.mercadolivre import MercadoLivreScraper
from src.scrapers.mock_gm import MockGMScraper
from src.scrapers.pecadireta import PecaDiretaScraper
from src.scrapers.procurapecas import ProcuraPecasScraper
from src.scrapers.vw import VWScraper

logger = structlog.get_logger()

# ─── Scraper Registry ─────────────────────────────────────────────

SCRAPER_REGISTRY: dict[SiteId, type[BaseScraper]] = {
    SiteId.GM: GMScraper,
    SiteId.MERCADO_LIVRE: MercadoLivreScraper,
    SiteId.VW: VWScraper,
    SiteId.EUROPE: EUImportsScraper,
    SiteId.PECA_DIRETA: PecaDiretaScraper,
    SiteId.MELIBOX: MeliboxScraper,
}

# Archived scrapers are kept for reference but are not runnable through the
# production registry or default demos.
ARCHIVED_SCRAPER_REGISTRY: dict[SiteId, type[BaseScraper]] = {
    SiteId.GOPARTS: GoPartsScraper,
    SiteId.PROCURA_PECAS: ProcuraPecasScraper,
    SiteId.EBAY: EbayScraper,
}

# Mock registry (remove when real credentials are available)
MOCK_REGISTRY: dict[SiteId, type[BaseScraper]] = {
    SiteId.GM: MockGMScraper,
}

# Active scraper instances (reused across requests for session persistence)
_active_scrapers: dict[SiteId, BaseScraper] = {}


def _should_use_mock(site_id: SiteId) -> bool:
    """Check if mock scraper should be used for this site."""
    if site_id not in MOCK_REGISTRY:
        return False
    return settings.mock_scrapers


async def get_scraper(site_id: SiteId) -> BaseScraper:
    """Get or create a scraper instance for the given site.

    Scrapers are cached to reuse authenticated browser sessions.
    Falls back to mock only when MOCK_SCRAPERS=true.
    """
    if site_id not in _active_scrapers:
        use_mock = _should_use_mock(site_id)
        scraper_class: type[BaseScraper]
        if use_mock:
            scraper_class = MOCK_REGISTRY[site_id]
            logger.info("Using mock scraper", site=site_id.value)
        else:
            registered_scraper_class = SCRAPER_REGISTRY.get(site_id)
            if registered_scraper_class is None:
                raise ValueError(f"No scraper registered for site: {site_id}")
            scraper_class = registered_scraper_class

        scraper = scraper_class()
        await scraper.initialize()
        _active_scrapers[site_id] = scraper
        logger.info("Scraper initialized", site=site_id.value, mock=use_mock)

    return _active_scrapers[site_id]


async def shutdown_all_scrapers() -> None:
    """Gracefully shut down all active scraper instances."""
    for site_id, scraper in _active_scrapers.items():
        try:
            await scraper.shutdown()
            logger.info("Scraper shut down", site=site_id.value)
        except Exception as e:
            logger.error("Error shutting down scraper", site=site_id.value, error=str(e))
    _active_scrapers.clear()


async def reset_scraper(site_id: SiteId) -> None:
    """Force re-initialization of a specific scraper (e.g., after auth failure)."""
    if site_id in _active_scrapers:
        await _active_scrapers[site_id].shutdown()
        del _active_scrapers[site_id]
    await get_scraper(site_id)  # Re-create
