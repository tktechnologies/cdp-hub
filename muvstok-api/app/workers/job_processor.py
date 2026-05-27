import asyncio
import logging
import time
from datetime import UTC, datetime
from uuid import UUID

import httpx

from app.clients.callback_client import CallbackClient
from app.clients.keyvault_client import KeyVaultClient
from app.clients.muvstok_client import MuvstokClient
from app.core.config import Settings, get_settings
from app.db.session import AsyncSessionLocal
from app.domain.job_status import JobStatus
from app.repositories.callback_repository import CallbackRepository
from app.repositories.error_repository import ErrorRepository
from app.repositories.job_repository import JobRepository
from app.repositories.muvstok_api_data_repository import MuvstokApiDataRepository
from app.repositories.snapshot_repository import SnapshotRepository
from app.services.auth_service import AuthService
from app.services.callback_service import CallbackService
from app.workers.sku_processor import SkuProcessor

logger = logging.getLogger("muvstok.job_processor")


class JobProcessor:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    async def process_job(self, job_id: UUID) -> None:
        keyvault_client: KeyVaultClient | None = None
        if self._should_use_keyvault():
            keyvault_client = KeyVaultClient(self._settings)

        muvstok_client = MuvstokClient(self._settings)
        callback_client = CallbackClient(self._settings)

        try:
            async with AsyncSessionLocal() as session:
                job_repo = JobRepository(session)
                job = await job_repo.get_job_model(job_id)

                if job.status in (JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELED):
                    logger.info(
                        "job_already_terminal",
                        extra={
                            "event_name": "job_already_terminal",
                            "job_id": str(job_id),
                            "status": job.status.value,
                        },
                    )
                    return

                if job.status == JobStatus.QUEUED:
                    await job_repo.mark_processing(job_id)

                auth_service = AuthService(self._settings, keyvault_client, muvstok_client)
                sku_processor = SkuProcessor(
                    auth_service=auth_service,
                    muvstok_client=muvstok_client,
                    snapshot_repository=SnapshotRepository(session),
                    api_data_repository=MuvstokApiDataRepository(session),
                    error_repository=ErrorRepository(session),
                )
                callback_service = CallbackService(
                    self._settings,
                    callback_client,
                    CallbackRepository(session),
                )

                token = await auth_service.get_token()
                items = await job_repo.list_actionable_items(job_id)
                sku_results = []
                processing_started_at = datetime.now(UTC)
                processing_started_perf = time.perf_counter()

                for item in items:
                    await job_repo.mark_item_processing(item.id)
                    try:
                        result, token = await sku_processor.process_item(
                            job_id=job_id,
                            correlation_id=job.correlation_id,
                            item=item,
                            token=token,
                        )
                    except httpx.HTTPStatusError as exc:
                        if exc.response.status_code in (401, 403):
                            token = await auth_service.get_token(force_refresh=True)
                            result, token = await sku_processor.process_item(
                                job_id=job_id,
                                correlation_id=job.correlation_id,
                                item=item,
                                token=token,
                            )
                        else:
                            raise
                    if result.status == "succeeded":
                        await job_repo.mark_item_succeeded(item.id)
                    else:
                        await job_repo.mark_item_failed(
                            item.id,
                            result.error_code or "failed",
                        )
                    sku_results.append(result)
                    await session.commit()
                    delay = self._settings.muvstok_sku_delay_seconds
                    if delay > 0:
                        await asyncio.sleep(delay)

                succeeded, failed = await job_repo.recount_job_items(job_id)
                if succeeded > 0 and failed > 0:
                    final_status = JobStatus.PARTIALLY_SUCCEEDED
                elif succeeded > 0:
                    final_status = JobStatus.SUCCEEDED
                else:
                    final_status = JobStatus.FAILED

                duration_seconds = round(time.perf_counter() - processing_started_perf, 2)
                callback_status = await callback_service.deliver_job_callback(
                    job_id=job.id,
                    correlation_id=job.correlation_id,
                    callback_url=job.callback_url,
                    job_status=final_status,
                    submitted_sku_count=job.submitted_sku_count,
                    sku_results=sku_results,
                    metadata=job.metadata_json,
                    started_at=processing_started_at,
                    duration_seconds=duration_seconds,
                )

                await job_repo.finalize_job(
                    job_id,
                    status=final_status,
                    callback_status=callback_status,
                    succeeded_sku_count=succeeded,
                    failed_sku_count=failed,
                )

                logger.info(
                    "job_completed",
                    extra={
                        "event_name": "job_completed",
                        "job_id": str(job_id),
                        "correlation_id": job.correlation_id,
                        "status": final_status.value,
                        "succeeded_sku_count": succeeded,
                        "failed_sku_count": failed,
                        "callback_status": callback_status.value,
                    },
                )
        finally:
            if keyvault_client is not None:
                await keyvault_client.close()

    def _should_use_keyvault(self) -> bool:
        if not self._settings.azure_key_vault_url.strip():
            return False
        has_env_creds = bool(
            self._settings.muvstok_user.strip() and self._settings.muvstok_password.strip()
        )
        return not has_env_creds
