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

    muvstok_base_url: str = "https://data-bi.muvstok.com.br/api/Demand/"
    muvstok_login_path: str = "https://api.integracao.muvstok.com.br/api/Auth/Login"
    muvstok_user: str = ""
    muvstok_password: str = ""
    muvstok_timeout_seconds: float = 30.0
    muvstok_token_ttl_hours: int = 24

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
