# Decisions

## Architecture

- Use FastAPI for the API container.
- Keep routes thin: API route -> service -> repository/client -> database or external service.
- Workers follow the same dependency direction: worker -> service -> repository/client -> database or external service.
- Store durable business state in PostgreSQL.
- Use Redis Streams for queue coordination in version 1.
- Use `app/` as the active production package.
- Keep legacy compatibility lookup routes deferred until the background job pipeline is stable.

## Queueing

- Redis Streams replaces Azure Service Bus for version 1 to reduce Azure service footprint and cost.
- Redis messages carry lightweight job references only.
- PostgreSQL owns all SKU item state.
- Workers acknowledge Redis messages only after the job reaches a durable terminal or resumable state.

## Data

- Jobs with thousands of SKUs are represented as thousands of `muvstok_job_items` rows.
- Raw Muvstok responses belong in JSONB snapshots with request, response, and governance metadata.
- Unique `(job_id, sku)` prevents duplicate SKU rows per job.
- Unique `(api_client_id, idempotency_key)` supports idempotent submissions.

## Security

- Store Muvstok tokens and credentials in Azure Key Vault.
- Store only Key Vault references and token lifecycle metadata in PostgreSQL.
- Never log tokens, API keys, passwords, connection strings, authorization headers, Key Vault values, or callback HMAC secrets.
- Callback URLs must be public HTTPS and validated to reduce SSRF risk.

## Azure

- Version 1 targets Azure Container Apps for API and worker containers.
- Use Azure Database for PostgreSQL Flexible Server for PostgreSQL.
- Use Azure Container Registry for images.
- Use Azure Monitor and Log Analytics for logs.
- Any new Azure service requires a short cost, reliability, and operational trade-off note.

## Agent Workspace

- Use `.agent/` as the canonical project-owned AI workspace.
- Keep `.agents/` ignored unless external tooling writes to it.
- Organize `.agent/` by memory, standards, workflows, skills, commands, sub-agents, and references.
