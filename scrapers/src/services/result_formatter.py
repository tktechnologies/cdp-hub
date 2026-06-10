"""Result formatting service — produces unified JSON output."""

from src.models.schemas import PartResult, SiteResult, SKUResult


def format_sku_result(
    sku: str,
    brand: str,
    site_results: list[SiteResult],
) -> SKUResult:
    """Aggregate site results into a unified SKUResult with best price.

    Args:
        sku: The searched SKU code
        brand: Part brand
        site_results: Results from each site

    Returns:
        Unified SKUResult with best_price identified
    """
    all_parts: list[PartResult] = []
    for sr in site_results:
        all_parts.extend(sr.results)

    best_price = _find_best_price(all_parts)

    return SKUResult(
        sku=sku,
        brand=brand,
        site_results=site_results,
        best_price=best_price,
        total_results=len(all_parts),
    )


def _find_best_price(results: list[PartResult]) -> PartResult | None:
    """Find the lowest-priced exact match when candidates share one currency."""
    priced = [r for r in results if r.price is not None and r.price > 0 and r.exact_match]
    if not priced:
        return None

    currencies = {r.currency for r in priced}
    if len(currencies) > 1:
        return None

    return min(priced, key=lambda r: r.price or 0.0)
