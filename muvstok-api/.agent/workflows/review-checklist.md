# Review Checklist

Lead with findings, ordered by severity.

## Check For

- Route handlers containing business logic.
- Services bypassing repositories or clients.
- Full SKU lists placed in Redis messages.
- Missing transaction safety or recovery around job/queue state.
- Unbounded memory use for large jobs.
- Missing idempotency behavior.
- Callback SSRF gaps.
- Secret leakage in logs, DB fields, errors, or test fixtures.
- Missing correlation IDs in logs or persisted state.
- Worker ack before durable terminal or resumable state.
- Missing tests for API validation, Redis behavior, workers, callbacks, and security.
- Claims of done without Azure-hosted validation.

## Review Output

- Findings first with file and line references.
- Open questions after findings.
- Change summary last, if useful.
- Mention test gaps or residual risk even when no findings are found.
