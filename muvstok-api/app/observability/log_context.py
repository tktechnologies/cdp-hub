from contextvars import ContextVar

correlation_id_context: ContextVar[str | None] = ContextVar("correlation_id", default=None)
job_id_context: ContextVar[str | None] = ContextVar("job_id", default=None)
