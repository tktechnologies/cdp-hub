"""Credential management — abstracts env vars and Vault."""

import structlog

from src.config import settings

logger = structlog.get_logger()


async def get_credentials(site_id: str) -> dict[str, str]:
    """Get credentials for a site from configured source.

    In simple mode: reads from environment variables.
    In vault mode: reads from HashiCorp Vault.

    Args:
        site_id: Site identifier (gm, ml, vw, eu)

    Returns:
        Dict with 'username', 'password', 'url' keys
    """
    if settings.use_vault:
        return await _get_from_vault(site_id)
    return settings.get_site_credentials(site_id)


async def _get_from_vault(site_id: str) -> dict[str, str]:
    """Fetch credentials from HashiCorp Vault.

    TODO: Implement Vault integration when moving to production.
    Requires: hvac library, VAULT_ADDR, VAULT_TOKEN env vars.
    """
    logger.warning("Vault integration not yet implemented, falling back to env vars")
    return settings.get_site_credentials(site_id)


def validate_credentials(site_id: str) -> bool:
    """Check if credentials are configured for a site."""
    creds = settings.get_site_credentials(site_id)
    has_creds = bool(creds.get("username") and creds.get("password"))
    if not has_creds:
        logger.warning("Missing credentials", site=site_id)
    return has_creds
