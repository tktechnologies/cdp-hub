from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.domain.job_status import (
    CallbackStatus,
    JobItemStatus,
    JobStatus,
    QueueMessageStatus,
    TokenStatus,
)


def enum_values(enum_class: type[StrEnum]) -> list[str]:
    return [member.value for member in enum_class]


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class ApiClient(Base, TimestampMixin):
    __tablename__ = "api_clients"

    id: Mapped[UUID] = mapped_column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, default=dict)


class MuvstokToken(Base, TimestampMixin):
    __tablename__ = "muvstok_tokens"

    id: Mapped[UUID] = mapped_column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    provider: Mapped[str] = mapped_column(String(100), nullable=False, default="muvstok")
    key_vault_secret_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[TokenStatus] = mapped_column(
        Enum(TokenStatus, values_callable=enum_values, name="token_status"), nullable=False
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_refresh_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, default=dict)

    __table_args__ = (Index("ix_muvstok_tokens_provider_status", "provider", "status"),)


class MuvstokJob(Base, TimestampMixin):
    __tablename__ = "muvstok_jobs"

    id: Mapped[UUID] = mapped_column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    correlation_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    api_client_id: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, values_callable=enum_values, name="job_status"),
        nullable=False,
        default=JobStatus.PENDING,
    )
    submitted_sku_count: Mapped[int] = mapped_column(Integer, nullable=False)
    succeeded_sku_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_sku_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    callback_url: Mapped[str] = mapped_column(Text, nullable=False)
    callback_status: Mapped[CallbackStatus | None] = mapped_column(
        Enum(CallbackStatus, values_callable=enum_values, name="callback_status"), nullable=True
    )
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, default=dict)

    items: Mapped[list["MuvstokJobItem"]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("api_client_id", "idempotency_key", name="uq_jobs_client_idempotency_key"),
        Index("ix_muvstok_jobs_status", "status"),
        Index("ix_muvstok_jobs_status_created_at", "status", "created_at"),
    )


class MuvstokJobItem(Base, TimestampMixin):
    __tablename__ = "muvstok_job_items"

    id: Mapped[UUID] = mapped_column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    job_id: Mapped[UUID] = mapped_column(ForeignKey("muvstok_jobs.id"), nullable=False, index=True)
    correlation_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    sku: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[JobItemStatus] = mapped_column(
        Enum(JobItemStatus, values_callable=enum_values, name="job_item_status"),
        nullable=False,
        default=JobItemStatus.PENDING,
    )
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, default=dict)

    job: Mapped[MuvstokJob] = relationship(back_populates="items")
    snapshots: Mapped[list["MuvstokRawSnapshot"]] = relationship(back_populates="job_item")
    api_data: Mapped["MuvstokApiData | None"] = relationship(back_populates="job_item")

    # No (job_id, sku) unique constraint: duplicate SKUs in one job are stored as
    # separate items so the callback returns one result per input row.
    __table_args__ = (Index("ix_muvstok_job_items_status_job_id", "status", "job_id"),)


class MuvstokRawSnapshot(Base, TimestampMixin):
    __tablename__ = "muvstok_raw_snapshots"

    id: Mapped[UUID] = mapped_column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    job_id: Mapped[UUID] = mapped_column(ForeignKey("muvstok_jobs.id"), nullable=False, index=True)
    job_item_id: Mapped[UUID] = mapped_column(
        ForeignKey("muvstok_job_items.id"), nullable=False, index=True
    )
    correlation_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    sku: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    request_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    response_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    raw_response: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    governance_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)

    job_item: Mapped[MuvstokJobItem] = relationship(back_populates="snapshots")


class MuvstokApiData(Base, TimestampMixin):
    __tablename__ = "muvstok_api_data"

    id: Mapped[UUID] = mapped_column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    job_id: Mapped[UUID] = mapped_column(ForeignKey("muvstok_jobs.id"), nullable=False, index=True)
    job_item_id: Mapped[UUID] = mapped_column(
        ForeignKey("muvstok_job_items.id"), nullable=False, index=True
    )
    correlation_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    sku: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    response_status: Mapped[str] = mapped_column(String(50), nullable=False)
    request_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    response_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    muvstok_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, default=dict)

    job_item: Mapped[MuvstokJobItem] = relationship(back_populates="api_data")

    __table_args__ = (
        UniqueConstraint("job_item_id", name="uq_muvstok_api_data_job_item_id"),
        Index("ix_muvstok_api_data_job_sku", "job_id", "sku"),
        Index("ix_muvstok_api_data_sku_created_at", "sku", "created_at"),
    )


class CallbackAttempt(Base, TimestampMixin):
    __tablename__ = "callback_attempts"

    id: Mapped[UUID] = mapped_column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    job_id: Mapped[UUID] = mapped_column(ForeignKey("muvstok_jobs.id"), nullable=False, index=True)
    correlation_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    status: Mapped[CallbackStatus] = mapped_column(
        Enum(CallbackStatus, values_callable=enum_values, name="callback_status"), nullable=False
    )
    attempt: Mapped[int] = mapped_column(Integer, nullable=False)
    callback_url: Mapped[str] = mapped_column(Text, nullable=False)
    response_status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, default=dict)


class AuditEvent(Base, TimestampMixin):
    __tablename__ = "audit_events"

    id: Mapped[UUID] = mapped_column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    correlation_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    job_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("muvstok_jobs.id"), nullable=True, index=True
    )
    event_name: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    actor: Mapped[str] = mapped_column(String(100), nullable=False, default="system")
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, default=dict)


class IngestionError(Base, TimestampMixin):
    __tablename__ = "ingestion_errors"

    id: Mapped[UUID] = mapped_column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    correlation_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    job_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("muvstok_jobs.id"), nullable=True, index=True
    )
    job_item_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("muvstok_job_items.id"), nullable=True, index=True
    )
    sku: Mapped[str | None] = mapped_column(String(128), nullable=True)
    error_code: Mapped[str] = mapped_column(String(100), nullable=False)
    error_type: Mapped[str] = mapped_column(String(100), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    retryable: Mapped[bool] = mapped_column(nullable=False, default=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, default=dict)


class QueueMessage(Base, TimestampMixin):
    __tablename__ = "queue_messages"

    id: Mapped[UUID] = mapped_column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    job_id: Mapped[UUID] = mapped_column(ForeignKey("muvstok_jobs.id"), nullable=False, index=True)
    correlation_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    queue_name: Mapped[str] = mapped_column(String(150), nullable=False)
    redis_message_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    status: Mapped[QueueMessageStatus] = mapped_column(
        Enum(QueueMessageStatus, values_callable=enum_values, name="queue_message_status"),
        nullable=False,
    )
    attempt: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    last_error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)

    __table_args__ = (Index("ix_queue_messages_status_created_at", "status", "created_at"),)
