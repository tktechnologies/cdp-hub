from enum import StrEnum


class JobStatus(StrEnum):
    PENDING = "pending"
    QUEUED = "queued"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    PARTIALLY_SUCCEEDED = "partially_succeeded"
    FAILED = "failed"
    CANCELED = "canceled"


class JobItemStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    RETRYING = "retrying"
    SKIPPED = "skipped"


class QueueMessageStatus(StrEnum):
    PUBLISHED = "published"
    CONSUMED = "consumed"
    ACKED = "acked"
    RETRYING = "retrying"
    DEAD_LETTERED = "dead_lettered"


class CallbackStatus(StrEnum):
    PENDING = "pending"
    SENDING = "sending"
    SUCCEEDED = "succeeded"
    RETRYING = "retrying"
    FAILED = "failed"


class TokenStatus(StrEnum):
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    REFRESHING = "refreshing"
    FAILED = "failed"
