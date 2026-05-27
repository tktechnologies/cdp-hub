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
        normalized: list[str] = []
        seen: set[str] = set()
        for raw_sku in value:
            sku = raw_sku.strip()
            if not sku:
                raise ValueError("SKU cannot be empty.")
            if len(sku) > 128:
                raise ValueError("SKU cannot exceed 128 characters.")
            if sku not in seen:
                normalized.append(sku)
                seen.add(sku)
        return normalized

    @field_validator("callback_url")
    @classmethod
    def validate_callback_url(cls, value: AnyHttpUrl) -> AnyHttpUrl:
        if not is_public_callback_url(str(value)):
            raise ValueError("Callback URL must be a public HTTPS URL.")
        return value


class LookupMuvstokSnapshotsRequest(BaseModel):
    skus: list[str] = Field(min_length=1)
