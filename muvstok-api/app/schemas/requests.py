from typing import Any

from pydantic import AnyHttpUrl, BaseModel, Field, field_validator

from app.core.security import is_public_callback_url


class CreateMuvstokJobRequest(BaseModel):
    skus: list[str] = Field(min_length=1)
    callback_url: AnyHttpUrl
    metadata: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str | None = Field(default=None, max_length=128)

    @field_validator("skus")
    @classmethod
    def normalize_skus(cls, value: list[str]) -> list[str]:
        # Duplicates are intentionally preserved: a job with N input SKUs must yield
        # N results (one per input row), even when SKUs repeat. The worker fetches each
        # unique SKU once and serves repeats from cache (in-job memo + Redis), so we keep
        # every occurrence here and let downstream caching avoid redundant upstream calls.
        normalized: list[str] = []
        for raw_sku in value:
            sku = raw_sku.strip()
            if not sku:
                raise ValueError("SKU cannot be empty.")
            if len(sku) > 128:
                raise ValueError("SKU cannot exceed 128 characters.")
            normalized.append(sku)
        return normalized

    @field_validator("callback_url")
    @classmethod
    def validate_callback_url(cls, value: AnyHttpUrl) -> AnyHttpUrl:
        if not is_public_callback_url(str(value)):
            raise ValueError("Callback URL must be a public HTTPS URL.")
        return value


class LookupMuvstokSnapshotsRequest(BaseModel):
    skus: list[str] = Field(min_length=1)
