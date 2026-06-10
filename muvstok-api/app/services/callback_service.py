import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import httpx

from app.clients.callback_client import CallbackClient
from app.core.config import Settings
from app.domain.job_status import CallbackStatus, JobStatus
from app.domain.sku_result_status import SkuResultStatus
from app.repositories.callback_repository import CallbackRepository
from app.schemas.callbacks import CallbackJobItem, MuvstokCallbackPayload
from app.services.governance_service import GovernanceService
from app.workers.sku_processor import SkuProcessResult

logger = logging.getLogger("muvstok.callback")


class CallbackService:
    def __init__(
        self,
        settings: Settings,
        callback_client: CallbackClient,
        callback_repository: CallbackRepository,
    ) -> None:
        self._settings = settings
        self._callback_client = callback_client
        self._callback_repository = callback_repository
        self._governance = GovernanceService()

    async def deliver_job_callback(
        self,
        *,
        job_id: UUID,
        correlation_id: str,
        callback_url: str,
        job_status: JobStatus,
        submitted_sku_count: int,
        sku_results: list[SkuProcessResult],
        metadata: dict[str, Any],
        started_at: datetime | None = None,
        duration_seconds: float | None = None,
    ) -> CallbackStatus:
        payload = self._build_payload(
            job_id=job_id,
            correlation_id=correlation_id,
            job_status=job_status,
            submitted_sku_count=submitted_sku_count,
            sku_results=sku_results,
            metadata=metadata,
            started_at=started_at,
            duration_seconds=duration_seconds,
        )
        payload_dict = payload.model_dump(mode="json")
        governance_issues = self._governance.validate_callback_payload(payload_dict)
        if governance_issues:
            logger.warning(
                "callback_governance_issues",
                extra={
                    "event_name": "callback_governance_issues",
                    "job_id": str(job_id),
                    "correlation_id": correlation_id,
                    "issue_count": len(governance_issues),
                    "issues": [
                        {"code": i.code, "message": i.message, "severity": i.severity}
                        for i in governance_issues
                    ],
                },
            )
            meta = dict(payload_dict.get("metadata") or {})
            meta["governance_issues"] = [
                {"code": i.code, "message": i.message, "severity": i.severity}
                for i in governance_issues
            ]
            payload_dict["metadata"] = meta
        secret = self._settings.callback_webhook_secret.strip()
        headers = {"x-webhook-secret": secret} if secret else None

        last_error: str | None = None
        for attempt in range(1, self._settings.callback_max_attempts + 1):
            try:
                response = await self._callback_client.post_callback(
                    callback_url,
                    payload_dict,
                    headers=headers,
                )
                await self._callback_repository.record_attempt(
                    job_id=job_id,
                    correlation_id=correlation_id,
                    status=CallbackStatus.SUCCEEDED,
                    attempt=attempt,
                    callback_url=callback_url,
                    response_status_code=response.status_code,
                )
                logger.info(
                    "callback_delivered",
                    extra={
                        "event_name": "callback_delivered",
                        "job_id": str(job_id),
                        "correlation_id": correlation_id,
                        "status_code": response.status_code,
                        "attempt": attempt,
                    },
                )
                return CallbackStatus.SUCCEEDED
            except httpx.HTTPError as exc:
                last_error = str(exc)
                await self._callback_repository.record_attempt(
                    job_id=job_id,
                    correlation_id=correlation_id,
                    status=CallbackStatus.RETRYING
                    if attempt < self._settings.callback_max_attempts
                    else CallbackStatus.FAILED,
                    attempt=attempt,
                    callback_url=callback_url,
                    error_code=type(exc).__name__,
                    metadata={"message": last_error},
                )
                logger.warning(
                    "callback_attempt_failed",
                    extra={
                        "event_name": "callback_attempt_failed",
                        "job_id": str(job_id),
                        "correlation_id": correlation_id,
                        "attempt": attempt,
                        "error": last_error,
                    },
                )

        logger.error(
            "callback_failed",
            extra={
                "event_name": "callback_failed",
                "job_id": str(job_id),
                "correlation_id": correlation_id,
                "error": last_error,
            },
        )
        return CallbackStatus.FAILED

    def _build_payload(
        self,
        *,
        job_id: UUID,
        correlation_id: str,
        job_status: JobStatus,
        submitted_sku_count: int,
        sku_results: list[SkuProcessResult],
        metadata: dict[str, Any],
        started_at: datetime | None = None,
        duration_seconds: float | None = None,
    ) -> MuvstokCallbackPayload:
        succeeded = sum(1 for row in sku_results if row.status == "succeeded")
        failed = sum(1 for row in sku_results if row.status != "succeeded")
        found = sum(1 for row in sku_results if row.sku_result == SkuResultStatus.FOUND_PRICE.value)
        no_price = sum(1 for row in sku_results if row.sku_result == SkuResultStatus.NO_PRICE.value)
        not_found = sum(
            1 for row in sku_results if row.sku_result == SkuResultStatus.NOT_FOUND.value
        )
        blocked = sum(1 for row in sku_results if row.sku_result == SkuResultStatus.BLOCKED.value)
        error = sum(
            1
            for row in sku_results
            if row.sku_result in {SkuResultStatus.ERROR.value, SkuResultStatus.TIMEOUT.value}
        )
        items = [
            CallbackJobItem(
                sku=row.sku,
                status=row.status,
                snapshot_id=row.snapshot_id,
                error_code=row.error_code,
                sku_result=row.sku_result,
                source_health=row.source_health,
                has_valid_price=row.has_valid_price,
            )
            for row in sku_results
        ]
        results = [
            {
                "sku": row.sku,
                "status": row.status,
                "sku_result": row.sku_result,
                "source_health": row.source_health,
                "has_valid_price": row.has_valid_price,
                "rows": row.rows or [],
                "duration_ms": row.duration_ms,
                "error_code": row.error_code,
            }
            for row in sku_results
        ]
        completed_at = datetime.now(UTC)
        resolved_duration = duration_seconds
        if resolved_duration is None and started_at is not None:
            resolved_duration = round((completed_at - started_at).total_seconds(), 2)
        return MuvstokCallbackPayload(
            job_id=job_id,
            correlation_id=correlation_id,
            status=job_status.value,
            submitted_sku_count=submitted_sku_count,
            succeeded_sku_count=succeeded,
            failed_sku_count=failed,
            found_sku_count=found,
            no_price_sku_count=no_price,
            not_found_sku_count=not_found,
            blocked_sku_count=blocked,
            error_sku_count=error,
            items=items,
            results=results,
            metadata=metadata,
            started_at=started_at,
            duration_seconds=resolved_duration,
            completed_at=completed_at,
        )
