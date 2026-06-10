"""Initial Muvstok ingestion schema.

Revision ID: 20260503_0001
Revises:
Create Date: 2026-05-03
"""

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260503_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


job_status = postgresql.ENUM(
    "pending",
    "queued",
    "processing",
    "succeeded",
    "partially_succeeded",
    "failed",
    "canceled",
    name="job_status",
    create_type=False,
)
job_item_status = postgresql.ENUM(
    "pending",
    "processing",
    "succeeded",
    "failed",
    "retrying",
    "skipped",
    name="job_item_status",
    create_type=False,
)
queue_message_status = postgresql.ENUM(
    "published",
    "consumed",
    "acked",
    "retrying",
    "dead_lettered",
    name="queue_message_status",
    create_type=False,
)
callback_status = postgresql.ENUM(
    "pending",
    "sending",
    "succeeded",
    "retrying",
    "failed",
    name="callback_status",
    create_type=False,
)
token_status = postgresql.ENUM(
    "active",
    "expired",
    "revoked",
    "refreshing",
    "failed",
    name="token_status",
    create_type=False,
)


def jsonb_default() -> sa.TextClause:
    return sa.text("'{}'::jsonb")


def timestamp_columns() -> list[sa.Column[Any]]:
    return [
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    ]


def upgrade() -> None:
    bind = op.get_bind()
    job_status.create(bind, checkfirst=True)
    job_item_status.create(bind, checkfirst=True)
    queue_message_status.create(bind, checkfirst=True)
    callback_status.create(bind, checkfirst=True)
    token_status.create(bind, checkfirst=True)

    op.create_table(
        "api_clients",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("key_hash", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("metadata", postgresql.JSONB(), server_default=jsonb_default(), nullable=False),
        *timestamp_columns(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key_hash"),
    )

    op.create_table(
        "muvstok_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=100), nullable=False),
        sa.Column("key_vault_secret_name", sa.String(length=255), nullable=False),
        sa.Column("status", token_status, nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_refresh_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), server_default=jsonb_default(), nullable=False),
        *timestamp_columns(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_muvstok_tokens_provider_status", "muvstok_tokens", ["provider", "status"], unique=False
    )

    op.create_table(
        "muvstok_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("correlation_id", sa.String(length=100), nullable=False),
        sa.Column("api_client_id", sa.String(length=100), nullable=False),
        sa.Column("status", job_status, nullable=False),
        sa.Column("submitted_sku_count", sa.Integer(), nullable=False),
        sa.Column("succeeded_sku_count", sa.Integer(), nullable=False),
        sa.Column("failed_sku_count", sa.Integer(), nullable=False),
        sa.Column("callback_url", sa.Text(), nullable=False),
        sa.Column("callback_status", callback_status, nullable=True),
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), server_default=jsonb_default(), nullable=False),
        *timestamp_columns(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "api_client_id", "idempotency_key", name="uq_jobs_client_idempotency_key"
        ),
    )
    op.create_index("ix_muvstok_jobs_correlation_id", "muvstok_jobs", ["correlation_id"])
    op.create_index("ix_muvstok_jobs_status_created_at", "muvstok_jobs", ["status", "created_at"])

    op.create_table(
        "muvstok_job_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("correlation_id", sa.String(length=100), nullable=False),
        sa.Column("sku", sa.String(length=128), nullable=False),
        sa.Column("status", job_item_status, nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("last_error_code", sa.String(length=100), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), server_default=jsonb_default(), nullable=False),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(["job_id"], ["muvstok_jobs.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_id", "sku", name="uq_muvstok_job_items_job_sku"),
    )
    op.create_index("ix_muvstok_job_items_correlation_id", "muvstok_job_items", ["correlation_id"])
    op.create_index("ix_muvstok_job_items_job_id", "muvstok_job_items", ["job_id"])
    op.create_index("ix_muvstok_job_items_status_job_id", "muvstok_job_items", ["status", "job_id"])

    op.create_table(
        "muvstok_raw_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("correlation_id", sa.String(length=100), nullable=False),
        sa.Column("sku", sa.String(length=128), nullable=False),
        sa.Column(
            "request_metadata", postgresql.JSONB(), server_default=jsonb_default(), nullable=False
        ),
        sa.Column(
            "response_metadata", postgresql.JSONB(), server_default=jsonb_default(), nullable=False
        ),
        sa.Column("raw_response", postgresql.JSONB(), nullable=False),
        sa.Column(
            "governance_metadata",
            postgresql.JSONB(),
            server_default=jsonb_default(),
            nullable=False,
        ),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(["job_id"], ["muvstok_jobs.id"]),
        sa.ForeignKeyConstraint(["job_item_id"], ["muvstok_job_items.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_muvstok_raw_snapshots_correlation_id", "muvstok_raw_snapshots", ["correlation_id"]
    )
    op.create_index("ix_muvstok_raw_snapshots_job_id", "muvstok_raw_snapshots", ["job_id"])
    op.create_index(
        "ix_muvstok_raw_snapshots_job_item_id", "muvstok_raw_snapshots", ["job_item_id"]
    )
    op.create_index("ix_muvstok_raw_snapshots_sku", "muvstok_raw_snapshots", ["sku"])

    op.create_table(
        "callback_attempts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("correlation_id", sa.String(length=100), nullable=False),
        sa.Column("status", callback_status, nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("callback_url", sa.Text(), nullable=False),
        sa.Column("response_status_code", sa.Integer(), nullable=True),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), server_default=jsonb_default(), nullable=False),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(["job_id"], ["muvstok_jobs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_callback_attempts_correlation_id", "callback_attempts", ["correlation_id"])
    op.create_index("ix_callback_attempts_job_id", "callback_attempts", ["job_id"])

    op.create_table(
        "audit_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("correlation_id", sa.String(length=100), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_name", sa.String(length=150), nullable=False),
        sa.Column("actor", sa.String(length=100), nullable=False),
        sa.Column("metadata", postgresql.JSONB(), server_default=jsonb_default(), nullable=False),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(["job_id"], ["muvstok_jobs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_events_correlation_id", "audit_events", ["correlation_id"])
    op.create_index("ix_audit_events_event_name", "audit_events", ["event_name"])
    op.create_index("ix_audit_events_job_id", "audit_events", ["job_id"])

    op.create_table(
        "ingestion_errors",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("correlation_id", sa.String(length=100), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("job_item_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("sku", sa.String(length=128), nullable=True),
        sa.Column("error_code", sa.String(length=100), nullable=False),
        sa.Column("error_type", sa.String(length=100), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("retryable", sa.Boolean(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(), server_default=jsonb_default(), nullable=False),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(["job_id"], ["muvstok_jobs.id"]),
        sa.ForeignKeyConstraint(["job_item_id"], ["muvstok_job_items.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ingestion_errors_correlation_id", "ingestion_errors", ["correlation_id"])
    op.create_index("ix_ingestion_errors_job_id", "ingestion_errors", ["job_id"])
    op.create_index("ix_ingestion_errors_job_item_id", "ingestion_errors", ["job_item_id"])

    op.create_table(
        "queue_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("correlation_id", sa.String(length=100), nullable=False),
        sa.Column("queue_name", sa.String(length=150), nullable=False),
        sa.Column("redis_message_id", sa.String(length=100), nullable=True),
        sa.Column("status", queue_message_status, nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("payload", postgresql.JSONB(), server_default=jsonb_default(), nullable=False),
        sa.Column("last_error_code", sa.String(length=100), nullable=True),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(["job_id"], ["muvstok_jobs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_queue_messages_correlation_id", "queue_messages", ["correlation_id"])
    op.create_index("ix_queue_messages_job_id", "queue_messages", ["job_id"])
    op.create_index("ix_queue_messages_redis_message_id", "queue_messages", ["redis_message_id"])
    op.create_index(
        "ix_queue_messages_status_created_at", "queue_messages", ["status", "created_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_queue_messages_status_created_at", table_name="queue_messages")
    op.drop_index("ix_queue_messages_redis_message_id", table_name="queue_messages")
    op.drop_index("ix_queue_messages_job_id", table_name="queue_messages")
    op.drop_index("ix_queue_messages_correlation_id", table_name="queue_messages")
    op.drop_table("queue_messages")

    op.drop_index("ix_ingestion_errors_job_item_id", table_name="ingestion_errors")
    op.drop_index("ix_ingestion_errors_job_id", table_name="ingestion_errors")
    op.drop_index("ix_ingestion_errors_correlation_id", table_name="ingestion_errors")
    op.drop_table("ingestion_errors")

    op.drop_index("ix_audit_events_job_id", table_name="audit_events")
    op.drop_index("ix_audit_events_event_name", table_name="audit_events")
    op.drop_index("ix_audit_events_correlation_id", table_name="audit_events")
    op.drop_table("audit_events")

    op.drop_index("ix_callback_attempts_job_id", table_name="callback_attempts")
    op.drop_index("ix_callback_attempts_correlation_id", table_name="callback_attempts")
    op.drop_table("callback_attempts")

    op.drop_index("ix_muvstok_raw_snapshots_sku", table_name="muvstok_raw_snapshots")
    op.drop_index("ix_muvstok_raw_snapshots_job_item_id", table_name="muvstok_raw_snapshots")
    op.drop_index("ix_muvstok_raw_snapshots_job_id", table_name="muvstok_raw_snapshots")
    op.drop_index("ix_muvstok_raw_snapshots_correlation_id", table_name="muvstok_raw_snapshots")
    op.drop_table("muvstok_raw_snapshots")

    op.drop_index("ix_muvstok_job_items_status_job_id", table_name="muvstok_job_items")
    op.drop_index("ix_muvstok_job_items_job_id", table_name="muvstok_job_items")
    op.drop_index("ix_muvstok_job_items_correlation_id", table_name="muvstok_job_items")
    op.drop_table("muvstok_job_items")

    op.drop_index("ix_muvstok_jobs_status_created_at", table_name="muvstok_jobs")
    op.drop_index("ix_muvstok_jobs_correlation_id", table_name="muvstok_jobs")
    op.drop_table("muvstok_jobs")

    op.drop_index("ix_muvstok_tokens_provider_status", table_name="muvstok_tokens")
    op.drop_table("muvstok_tokens")
    op.drop_table("api_clients")

    token_status.drop(op.get_bind(), checkfirst=True)
    callback_status.drop(op.get_bind(), checkfirst=True)
    queue_message_status.drop(op.get_bind(), checkfirst=True)
    job_item_status.drop(op.get_bind(), checkfirst=True)
    job_status.drop(op.get_bind(), checkfirst=True)
