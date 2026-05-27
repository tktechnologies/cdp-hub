# Coding Standards

## Architecture

- Keep business logic out of route handlers.
- Follow the dependency direction: route or worker -> service -> repository/client -> database, Redis, Muvstok, or Azure service.
- Prefer small production-shaped changes over scaffolding that does not run.
- Keep large-job behavior streaming or batched; never load unbounded SKU data into memory.

## Python

- Use typed, explicit interfaces for service, repository, and client boundaries.
- Keep async database and external I/O paths consistent with existing project patterns.
- Prefer structured validation through Pydantic models over ad hoc parsing.
- Use Python 3.12.
- Keep ruff line length at 100 characters.
- Preserve mypy strictness.
- Add comments only where they explain non-obvious behavior.

## Data And Security

- Do not persist raw secrets, API keys, passwords, connection strings, tokens, authorization headers, Key Vault values, or callback HMAC secrets.
- Store raw Muvstok responses in JSONB snapshots with enough metadata for audit and replay.
- Preserve correlation IDs through API, services, repositories, queues, logs, and callbacks.

## Observability

- Add structured logs for job lifecycle, queue transitions, worker progress, callback attempts, and error classifications.
- Include useful operational identifiers, but redact secrets and sensitive headers.
- Add metrics and traces when behavior crosses API, worker, database, Redis, Muvstok, or callback boundaries.
