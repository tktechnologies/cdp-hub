from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "API Diversos"
    app_version: str = "0.1.0"
    environment: str = "development"
    enable_docs: bool = True

    api_keys: str = Field(default="", description="Comma-separated API keys for initial auth.")

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/muvstok"

    # Redis DB 0 — see docs/DATABASE.md for platform key layout.
    redis_url: str = "redis://localhost:6379/0"
    # Stream keys (not scrape:v1: / dispatch:run: — those are scraper-owned).
    redis_job_stream: str = "muvstok:jobs"
    redis_job_consumer_group: str = "muvstok-workers"
    redis_dead_letter_stream: str = "muvstok:jobs:dead-letter"
    redis_consumer_name: str = "worker-1"
    redis_pending_idle_ms: int = 300_000
    worker_jobs_per_read: int = 1
    muvstok_sku_delay_seconds: float = 0.75

    max_skus_per_job: int = 10_000
    job_item_batch_size: int = 250

    # Per-SKU result cache (holds Muvstok prices to avoid re-requesting duplicates and
    # repeats within the TTL window). In-job duplicates are always served from an in-memory
    # memo; this Redis layer additionally serves cross-job repeats. Mirrors the scraper's
    # 24h scrape cache. Falls back to redis_url (DB 0) when muvstok_cache_redis_url is empty;
    # keys use a distinct "muvstok:sku:" prefix so they never collide with the job streams.
    muvstok_cache_enabled: bool = True
    muvstok_cache_redis_url: str = ""
    muvstok_cache_ttl_seconds: int = 86_400
    muvstok_cache_ttl_not_found_seconds: int = 21_600

    @property
    def sku_cache_redis_url(self) -> str:
        return self.muvstok_cache_redis_url.strip() or self.redis_url

    muvstok_base_url: str = "https://data-bi.muvstok.com.br/api/Demand/"
    muvstok_login_path: str = "https://api.integracao.muvstok.com.br/api/Auth/Login"
    muvstok_user: str = ""
    muvstok_password: str = ""
    muvstok_timeout_seconds: float = 30.0
    muvstok_token_ttl_hours: int = 24
    muvstok_dealership_directory_enabled: bool = True
    muvstok_dealership_directory_url: str = (
        "https://docs.google.com/spreadsheets/d/"
        "1p76idxvF0z8nl20L1jvNw8CABjbgsf-R/export?format=csv&gid=1843593319"
    )
    muvstok_dealership_directory_ttl_seconds: int = 86_400

    azure_key_vault_url: str = ""
    key_vault_token_secret_name: str = "muvstok-api-token"
    key_vault_muvstok_user_secret_name: str = "muvstok-user"
    key_vault_muvstok_password_secret_name: str = "muvstok-password"

    callback_webhook_secret: str = ""
    callback_timeout_seconds: float = 30.0
    callback_max_attempts: int = 5

    @property
    def api_key_values(self) -> tuple[str, ...]:
        return tuple(key.strip() for key in self.api_keys.split(",") if key.strip())


@lru_cache
def get_settings() -> Settings:
    return Settings()
