"""Application configuration via environment variables."""

from pathlib import Path
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration. Reads from .env file and environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @field_validator("api_key", "callback_webhook_secret", mode="before")
    @classmethod
    def _strip_credential(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().strip("\r\n")
        return value

    # --- Database ---
    database_url: str = "postgresql+asyncpg://cdp:cdp_pass@localhost:5432/cdp_scraper"
    database_url_sync: str = "postgresql://cdp:cdp_pass@localhost:5432/cdp_scraper"

    # --- Redis ---
    redis_url: str = "redis://localhost:6379/0"
    scrape_cache_redis_url: str = "redis://localhost:6379/1"

    # --- Job Execution ---
    job_execution_backend: Literal["local", "celery"] = "local"
    celery_broker_url: str | None = None
    celery_result_backend: str | None = None
    celery_worker_prefetch_multiplier: int = 1
    celery_task_time_limit_seconds: int = 3600

    # --- API ---
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_workers: int = 2
    api_key: str = "dev-key-change-in-production"
    cors_allowed_origins: list[str] = ["http://localhost:3000"]  # Restrict in production

    # --- Playwright ---
    playwright_headless: bool = True
    playwright_slow_mo_ms: int = 0
    browser_state_dir: Path = Path("./browser_states")
    screenshot_on_error: bool = True
    browser_locale: str = "pt-BR"
    browser_timezone_id: str = "America/Sao_Paulo"
    browser_accept_language: str = "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7"
    browser_viewport_width: int = 1920
    browser_viewport_height: int = 1080
    browser_user_agents: list[str] = []
    browser_extra_http_headers_enabled: bool = True
    browser_stealth_enabled: bool = True

    # --- Mock Mode (for testing, remove for production) ---
    mock_scrapers: bool = False

    # --- Site Credentials (Simple Mode) ---
    credential_gm_user: str = ""
    credential_gm_pass: str = ""
    credential_gm_url: str = "https://www.pecachevrolet.com.br"

    credential_ml_user: str = ""
    credential_ml_pass: str = ""
    credential_ml_url: str = "https://lista.mercadolivre.com.br"

    credential_goparts_user: str = ""
    credential_goparts_pass: str = ""
    credential_goparts_url: str = "https://goparts.com.br"

    credential_vw_user: str = ""
    credential_vw_pass: str = ""
    credential_vw_url: str = "https://pecas.vw.com.br"

    credential_eu_user: str = ""
    credential_eu_pass: str = ""
    credential_eu_url: str = "https://export.fastparts.is"

    credential_procurapecas_user: str = ""
    credential_procurapecas_pass: str = ""
    credential_procurapecas_url: str = "https://www.procurapecas.com.br"

    credential_pecadireta_user: str = ""
    credential_pecadireta_pass: str = ""
    credential_pecadireta_url: str = "https://www.pecadireta.com.br"

    credential_ebay_user: str = ""
    credential_ebay_pass: str = ""
    credential_ebay_url: str = "https://www.ebay.com"

    credential_melibox_user: str = ""
    credential_melibox_pass: str = ""
    credential_melibox_url: str = "https://app.melibox.com.br"

    # --- Vault (Optional) ---
    vault_addr: str | None = None
    vault_token: str | None = None
    vault_mount: str = "secret"
    vault_path: str = "cdp/scrapers"

    # --- CDP Integration ---
    cdp_api_url: str = "http://localhost:3000/api/v1"
    cdp_api_key: str = ""

    # --- Logging ---
    log_level: str = "INFO"
    log_format: str = "json"

    # --- External Callback ---
    callback_webhook_secret: str = "changeme"
    demo_callback_url: str = "https://automacao.tktechnologies.com.br/webhook/scraper-result"

    # --- Monitoring ---
    enable_metrics: bool = True
    metrics_port: int = 9090

    # --- Scraper Behavior ---
    max_concurrent_scrapers: int = 1  # Live sites per SKU when SCRAPE_SITES_SEQUENTIAL=false
    scrape_timeout_seconds: int = 120
    retry_max_attempts: int = 3
    retry_wait_seconds: int = 5
    session_ttl_hours: int = 12
    session_recheck_seconds: int = 900  # Skip live session probe within worker TTL
    scrape_delay_min: float = 4.0  # Min seconds between SKU searches
    scrape_delay_max: float = 10.0  # Max seconds between SKU searches
    scraper_action_delay_min_ms: int = 600
    scraper_action_delay_max_ms: int = 1800
    anti_bot_retry_attempts: int = 1
    anti_bot_backoff_min_seconds: float = 5.0
    anti_bot_backoff_max_seconds: float = 15.0
    anti_bot_block_status_codes: list[int] = [403, 429]
    melibox_sku_delay_min: float = 3.0
    melibox_sku_delay_max: float = 8.0
    melibox_rotate_context_per_sku: bool = False
    scrape_sites_sequential: bool = True

    # --- Scrape result cache (Redis, anti-bot) ---
    scrape_cache_enabled: bool = True
    scrape_cache_ttl_seconds: int = 86400
    scrape_cache_ttl_not_found_seconds: int = 21600
    scrape_cache_ttl_blocked_seconds: int = 1800
    scrape_cache_pg_fallback: bool = True
    scrape_cache_bypass_statuses: list[str] = ["error", "timeout"]

    # --- Proxy Rotation ---
    proxy_rotation_enabled: bool = False
    proxy_urls: list[str] = []
    proxy_bypass: str = "localhost,127.0.0.1"
    proxy_fail_closed: bool = False
    proxy_affinity_enabled: bool = True
    proxy_state_per_identity: bool = True
    anti_bot_circuit_breaker_enabled: bool = True
    anti_bot_circuit_breaker_threshold: int = 3
    anti_bot_circuit_breaker_cooldown_seconds: int = 1800

    @property
    def resolved_celery_broker_url(self) -> str:
        """Celery broker URL, defaulting to the configured Redis URL."""
        return self.celery_broker_url or self.redis_url

    @property
    def resolved_celery_result_backend(self) -> str:
        """Celery result backend URL, defaulting to the configured Redis URL."""
        return self.celery_result_backend or self.redis_url

    @property
    def use_vault(self) -> bool:
        """Whether to use HashiCorp Vault for credential storage."""
        return self.vault_addr is not None and self.vault_token is not None

    def get_site_credentials(self, site_id: str) -> dict[str, str]:
        """Get credentials for a specific site."""
        prefix = f"credential_{site_id}_"
        return {
            "username": getattr(self, f"{prefix}user", ""),
            "password": getattr(self, f"{prefix}pass", ""),
            "url": getattr(self, f"{prefix}url", ""),
        }


settings = Settings()
