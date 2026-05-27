"""Helpers for Muvstok Demand API request/response parsing."""

from __future__ import annotations

from typing import Any


def extract_access_token(payload: Any) -> str:
    candidates: list[dict[str, Any]] = []
    if isinstance(payload, dict):
        candidates.append(payload)
        for nested_key in ("data", "result", "payload"):
            nested = payload.get(nested_key)
            if isinstance(nested, dict):
                candidates.append(nested)

    for candidate in candidates:
        for key in ("accessToken", "access_token", "token", "jwt"):
            value = candidate.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return ""


def extract_demand_rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict):
        for key in ("data", "items", "results", "demand"):
            nested = payload.get(key)
            if isinstance(nested, list):
                return [row for row in nested if isinstance(row, dict)]
        if "sku" in payload or "skuSemCaractereEspecial" in payload:
            return [payload]
    return []


def is_auth_failure(status_code: int, body_text: str) -> bool:
    if status_code in (401, 403):
        return True
    if status_code < 400:
        return False
    lowered = body_text.lower()
    return "token" in lowered and any(
        term in lowered for term in ("invalid", "expired", "bearer", "unauthor")
    )
