# Azure Playbook

## Version 1 Services

- FastAPI API container on Azure Container Apps.
- Worker container on Azure Container Apps.
- PostgreSQL on Azure Database for PostgreSQL Flexible Server.
- Azure Key Vault for secrets.
- Redis for Redis Streams queueing.
- Azure Container Registry for images.
- Azure Monitor and Log Analytics for logs.

## Rules

- Do not add Azure Service Bus for version 1.
- Any new Azure service requires a short cost, reliability, and operational trade-off note.
- Use Managed Identity in Azure where possible.
- Store secrets in Key Vault and keep only references or metadata in PostgreSQL.
- Run official validation against Azure-hosted API, worker, PostgreSQL, Redis, and Key Vault-compatible test resources.

## Redis Options

- Lower-cost option: self-host Redis as a container or VM with persistence and monitoring.
- More reliable option: managed Redis service, with explicit cost approval.
