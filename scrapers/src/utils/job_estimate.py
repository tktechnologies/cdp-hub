"""Shared cold-run job duration estimates for API and operator messaging."""

from src.config import settings

# Conservative max seconds per parallel wave (VW-heavy batches).
DEFAULT_SECONDS_PER_WAVE = 18.0


def estimate_job_duration_seconds(
    item_count: int,
    site_count: int,
    *,
    scrape_sites_sequential: bool | None = None,
    max_concurrent_scrapers: int | None = None,
    scrape_delay_min: float | None = None,
    scrape_delay_max: float | None = None,
    seconds_per_site_wave: float = DEFAULT_SECONDS_PER_WAVE,
) -> int:
    """Estimate wall-clock seconds for a cold scrape job (no cache hits)."""
    items = max(1, item_count)
    sites = max(1, site_count)
    sequential = (
        settings.scrape_sites_sequential
        if scrape_sites_sequential is None
        else scrape_sites_sequential
    )
    concurrency = max(
        1,
        settings.max_concurrent_scrapers
        if max_concurrent_scrapers is None
        else max_concurrent_scrapers,
    )
    delay_min = settings.scrape_delay_min if scrape_delay_min is None else scrape_delay_min
    delay_max = settings.scrape_delay_max if scrape_delay_max is None else scrape_delay_max
    inter_sku_delay = (delay_min + delay_max) / 2

    if sequential:
        site_seconds_per_item = sites * 12.0
    else:
        import math

        waves = math.ceil(sites / concurrency)
        site_seconds_per_item = waves * seconds_per_site_wave

    per_item = site_seconds_per_item + inter_sku_delay
    return max(30, int(items * per_item))
