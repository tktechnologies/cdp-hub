import time
from dataclasses import dataclass, replace
from typing import Any
from uuid import UUID

import httpx

from app.clients.muvstok_client import MuvstokClient
from app.db.models import MuvstokJobItem
from app.domain.muvstok_api import is_auth_failure
from app.repositories.error_repository import ErrorRepository
from app.repositories.muvstok_api_data_repository import MuvstokApiDataRepository
from app.repositories.snapshot_repository import SnapshotRepository
from app.services.auth_service import AuthService
from app.services.governance_service import GovernanceService


@dataclass(slots=True)
class SkuProcessResult:
    sku: str
    status: str
    error_code: str | None
    rows: list[dict[str, Any]]
    snapshot_id: UUID | None
    duration_ms: int = 0


class SkuProcessor:
    def __init__(
        self,
        auth_service: AuthService,
        muvstok_client: MuvstokClient,
        snapshot_repository: SnapshotRepository,
        api_data_repository: MuvstokApiDataRepository,
        error_repository: ErrorRepository,
    ) -> None:
        self._auth_service = auth_service
        self._muvstok_client = muvstok_client
        self._snapshot_repository = snapshot_repository
        self._api_data_repository = api_data_repository
        self._error_repository = error_repository
        self._governance = GovernanceService()

    async def process_item(
        self,
        *,
        job_id: UUID,
        correlation_id: str,
        item: MuvstokJobItem,
        token: str,
    ) -> tuple[SkuProcessResult, str]:
        sku = item.sku
        started = time.perf_counter()

        def _timed(result: SkuProcessResult) -> SkuProcessResult:
            elapsed_ms = max(0, int((time.perf_counter() - started) * 1000))
            return replace(result, duration_ms=elapsed_ms)

        try:
            rows, status_code = await self._muvstok_client.fetch_sku(sku, token)
            if is_auth_failure(status_code, ""):
                refreshed = await self._auth_service.get_token(force_refresh=True)
                rows, status_code = await self._muvstok_client.fetch_sku(sku, refreshed)
                token = refreshed

            if status_code == 404 or not rows:
                await self._persist_not_found(job_id, correlation_id, item)
                return (
                    _timed(
                        SkuProcessResult(
                            sku=sku,
                            status="failed",
                            error_code="not_found",
                            rows=[],
                            snapshot_id=None,
                        )
                    ),
                    token,
                )

            governance_issues = self._governance.validate_listing_rows(sku, rows)
            snapshot = await self._snapshot_repository.save_snapshot(
                job_id=job_id,
                job_item_id=item.id,
                correlation_id=correlation_id,
                sku=sku,
                raw_response={"rows": rows, "status_code": status_code},
                response_metadata={
                    "row_count": len(rows),
                    "governance_issues": [
                        {"code": i.code, "message": i.message, "severity": i.severity}
                        for i in governance_issues
                    ],
                },
            )
            result = _timed(
                SkuProcessResult(
                    sku=sku,
                    status="succeeded",
                    error_code=None,
                    rows=rows,
                    snapshot_id=snapshot.id,
                )
            )
            await self._api_data_repository.save_result(
                job_id=job_id,
                job_item_id=item.id,
                correlation_id=correlation_id,
                sku=sku,
                response_status="succeeded",
                muvstok_payload={"rows": rows},
                response_metadata={
                    "row_count": len(rows),
                    "duration_ms": result.duration_ms,
                },
            )
            return (result, token)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code in (401, 403):
                raise
            await self._record_failure(
                job_id=job_id,
                correlation_id=correlation_id,
                item=item,
                error_code=f"http_{exc.response.status_code}",
                message=str(exc),
            )
            return (
                _timed(
                    SkuProcessResult(
                        sku=sku,
                        status="failed",
                        error_code=f"http_{exc.response.status_code}",
                        rows=[],
                        snapshot_id=None,
                    )
                ),
                token,
            )
        except Exception as exc:
            await self._record_failure(
                job_id=job_id,
                correlation_id=correlation_id,
                item=item,
                error_code=type(exc).__name__,
                message=str(exc),
            )
            return (
                _timed(
                    SkuProcessResult(
                        sku=sku,
                        status="failed",
                        error_code=type(exc).__name__,
                        rows=[],
                        snapshot_id=None,
                    )
                ),
                token,
            )

    async def _persist_not_found(
        self,
        job_id: UUID,
        correlation_id: str,
        item: MuvstokJobItem,
    ) -> None:
        await self._api_data_repository.save_result(
            job_id=job_id,
            job_item_id=item.id,
            correlation_id=correlation_id,
            sku=item.sku,
            response_status="not_found",
            muvstok_payload={"rows": []},
            response_metadata={"reason": "not_found"},
        )

    async def _record_failure(
        self,
        *,
        job_id: UUID,
        correlation_id: str,
        item: MuvstokJobItem,
        error_code: str,
        message: str,
    ) -> None:
        await self._error_repository.record_error(
            correlation_id=correlation_id,
            job_id=job_id,
            job_item_id=item.id,
            sku=item.sku,
            error_code=error_code,
            error_type="sku_processing",
            message=message,
            retryable=False,
        )
        await self._api_data_repository.save_result(
            job_id=job_id,
            job_item_id=item.id,
            correlation_id=correlation_id,
            sku=item.sku,
            response_status="failed",
            muvstok_payload={"error_code": error_code, "message": message},
            response_metadata={},
        )
