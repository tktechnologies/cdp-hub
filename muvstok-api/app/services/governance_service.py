from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class GovernanceIssue:
    code: str
    message: str
    severity: str = "warning"


class GovernanceService:
    """Consistency checks for Muvstok payloads and listing rows."""

    def validate_listing_rows(self, sku: str, rows: list[dict[str, Any]]) -> list[GovernanceIssue]:
        issues: list[GovernanceIssue] = []
        if not rows:
            return issues
        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                issues.append(
                    GovernanceIssue(
                        code="invalid_row_type",
                        message=f"SKU {sku} row {index} is not an object",
                        severity="error",
                    )
                )
                continue
            price = row.get("valorPrecoVenda") if row.get("valorPrecoVenda") is not None else row.get("price")
            if price is not None:
                try:
                    if float(price) < 0:
                        issues.append(
                            GovernanceIssue(
                                code="negative_price",
                                message=f"SKU {sku} row {index} has negative price",
                            )
                        )
                except (TypeError, ValueError):
                    issues.append(
                        GovernanceIssue(
                            code="invalid_price",
                            message=f"SKU {sku} row {index} has non-numeric price",
                        )
                    )
            branch = row.get("nomeFilial") or row.get("branch_name")
            if not branch:
                issues.append(
                    GovernanceIssue(
                        code="missing_branch",
                        message=f"SKU {sku} row {index} missing branch name",
                    )
                )
        return issues

    def validate_callback_payload(self, payload: dict[str, Any]) -> list[GovernanceIssue]:
        issues: list[GovernanceIssue] = []
        submitted = int(payload.get("submitted_sku_count") or 0)
        succeeded = int(payload.get("succeeded_sku_count") or 0)
        failed = int(payload.get("failed_sku_count") or 0)
        if submitted > 0 and succeeded + failed != submitted:
            issues.append(
                GovernanceIssue(
                    code="sku_count_mismatch",
                    message=(
                        f"submitted={submitted} but succeeded+failed={succeeded + failed}"
                    ),
                    severity="error",
                )
            )
        items = payload.get("items")
        if isinstance(items, list) and submitted > 0 and len(items) != submitted:
            issues.append(
                GovernanceIssue(
                    code="items_length_mismatch",
                    message=f"submitted={submitted} but items length={len(items)}",
                    severity="error",
                )
            )
        results = payload.get("results")
        if isinstance(results, list):
            for entry in results:
                if not isinstance(entry, dict):
                    continue
                sku = str(entry.get("sku") or "")
                rows = entry.get("rows") if isinstance(entry.get("rows"), list) else []
                if entry.get("status") in ("succeeded", "success") and not rows:
                    issues.append(
                        GovernanceIssue(
                            code="succeeded_without_rows",
                            message=f"SKU {sku} marked succeeded but results rows empty",
                            severity="error",
                        )
                    )
        return issues
