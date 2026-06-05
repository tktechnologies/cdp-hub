from enum import StrEnum
from typing import Any


class SkuResultStatus(StrEnum):
    FOUND_PRICE = "FOUND_PRICE"
    NO_PRICE = "NO_PRICE"
    NOT_FOUND = "NOT_FOUND"
    BLOCKED = "BLOCKED"
    TIMEOUT = "TIMEOUT"
    ERROR = "ERROR"
    NOT_QUERIED = "NOT_QUERIED"


class SourceHealth(StrEnum):
    WORKING = "WORKING"
    BLOCKED = "BLOCKED"
    TIMEOUT = "TIMEOUT"
    ERROR = "ERROR"
    NOT_QUERIED = "NOT_QUERIED"


def _row_price(row: dict[str, Any]) -> float | None:
    price = row.get("valorPrecoVenda") if row.get("valorPrecoVenda") is not None else row.get("price")
    if price is None or price == "":
        return None
    try:
        return float(price)
    except (TypeError, ValueError):
        return None


def _has_positive_price(rows: list[dict[str, Any]]) -> bool:
    for row in rows:
        if not isinstance(row, dict):
            continue
        price = _row_price(row)
        if price is not None and price > 0:
            return True
    return False


def classify_rows(rows: list[dict[str, Any]]) -> tuple[SkuResultStatus, SourceHealth, bool]:
    if not rows:
        return SkuResultStatus.NOT_FOUND, SourceHealth.WORKING, False
    if _has_positive_price(rows):
        return SkuResultStatus.FOUND_PRICE, SourceHealth.WORKING, True
    return SkuResultStatus.NO_PRICE, SourceHealth.WORKING, False


def classify_failure(error_code: str) -> tuple[SkuResultStatus, SourceHealth]:
    code = (error_code or "").lower()
    if "timeout" in code or "timed out" in code:
        return SkuResultStatus.TIMEOUT, SourceHealth.TIMEOUT
    if "403" in code or "blocked" in code or "forbidden" in code:
        return SkuResultStatus.BLOCKED, SourceHealth.BLOCKED
    return SkuResultStatus.ERROR, SourceHealth.ERROR
