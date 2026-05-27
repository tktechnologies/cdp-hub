# Azure Infrastructure

## Version 1 Direction

- FastAPI API container on Azure Container Apps.
- The Muvstok FastAPI API container is separate from the existing scraper FastAPI API container.
- Worker container on Azure Container Apps.
- PostgreSQL on Azure Database for PostgreSQL Flexible Server.
- Azure Key Vault for secrets.
- Redis for queueing, preferably Redis Streams.
- Azure Container Registry for images.
- Azure Monitor and Log Analytics for logs.

## Container Boundary

- Keep the existing scraper API as its own Azure Container App.
- Deploy this repository as a separate Muvstok API Azure Container App with its own image, environment variables, scaling rules, logs, and health checks.
- The two FastAPI containers can point at the same PostgreSQL database when business matching requires it.
- The Muvstok API writes Muvstok-owned records, including `muvstok_api_data`; the scraper API must not write to Muvstok-owned tables.

## Redis Deployment Options

- Lower-cost option: self-host Redis as a container or VM with persistence and monitoring.
- More reliable option: managed Redis service, with explicit cost approval.

## Cost Rule

Do not add Azure Service Bus for version 1. Any new Azure service requires a short cost, reliability, and operational trade-off note.

## Test Environment

CI/CD must run tests against Azure-hosted API, worker, PostgreSQL, Redis, and Key Vault-compatible test resources.
