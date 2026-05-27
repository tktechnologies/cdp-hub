"""SKU validation and normalization service.

Centralizes all business rules for SKU handling:
- Exact match validation
- Mercedes code normalization for European sites
- Character stripping and normalization
"""

import re

import structlog

from src.models.schemas import SiteId

logger = structlog.get_logger()

# Characters to strip from SKU codes during normalization
_STRIP_PATTERN = re.compile(r"[\s\-\.\\/]")


def normalize_sku(sku: str, brand: str = "", site_id: SiteId | None = None) -> str:
    """Normalize a SKU code by removing special characters and applying business rules.

    Args:
        sku: Raw SKU code from input
        brand: Part brand (triggers Mercedes rule)
        site_id: Target site (triggers EU-specific rules)

    Returns:
        Normalized SKU string ready for search

    Business Rules:
        1. Strip whitespace, hyphens, dots, slashes
        2. Convert to uppercase
        3. Mercedes + EUROPE site: remove first character
    """
    normalized = _STRIP_PATTERN.sub("", sku.strip()).upper()

    # BR-02: Mercedes code — remove first character for European site
    if (
        brand.lower() in ("mercedes", "mb", "mercedes-benz")
        and site_id == SiteId.EUROPE
        and len(normalized) > 1
    ):
        original = normalized
        normalized = normalized[1:]
        logger.debug(
            "Mercedes SKU adjusted for EU",
            original=original,
            normalized=normalized,
        )

    return normalized


def validate_exact_match(searched_sku: str, found_sku: str) -> bool:
    """Check if found SKU exactly matches searched SKU after normalization.

    Both SKUs are normalized (strip special chars, uppercase) before comparison.
    This is the primary validation — partial/similar matches are REJECTED.

    Args:
        searched_sku: The SKU we searched for
        found_sku: The SKU returned by the site

    Returns:
        True only if normalized forms are identical
    """
    clean_searched = _STRIP_PATTERN.sub("", searched_sku.strip()).upper()
    clean_found = _STRIP_PATTERN.sub("", found_sku.strip()).upper()
    return clean_searched == clean_found


def parse_brazilian_price(price_text: str) -> float:
    """Parse Brazilian Real price format to float.

    Handles: R$ 1.234,56 → 1234.56
    Brazilian format uses dots as thousands separator and comma as decimal.

    Args:
        price_text: Raw price string (e.g., "R$ 1.234,56")

    Returns:
        Float value (e.g., 1234.56). Returns 0.0 on parse failure.
    """
    cleaned = re.sub(r"[^\d,.]", "", price_text)
    # Remove thousands dots, convert decimal comma to dot
    cleaned = cleaned.replace(".", "").replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        logger.warning("Failed to parse price", price_text=price_text)
        return 0.0


def parse_usd_eur_price(price_text: str) -> float:
    """Parse USD/EUR price format to float.

    Handles: $1,234.56 or €1,234.56 → 1234.56
    US/EU format uses commas as thousands separator and dot as decimal.

    Args:
        price_text: Raw price string (e.g., "$1,234.56")

    Returns:
        Float value. Returns 0.0 on parse failure.
    """
    cleaned = re.sub(r"[^\d,.]", "", price_text)
    # Remove thousands commas
    cleaned = cleaned.replace(",", "")
    try:
        return float(cleaned)
    except ValueError:
        logger.warning("Failed to parse price", price_text=price_text)
        return 0.0
