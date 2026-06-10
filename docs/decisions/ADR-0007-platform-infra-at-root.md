# ADR-0007: Platform infrastructure at repo root

**Status:** Accepted  
**Date:** 2026-06-09

## Context

Azure Bicep for the CDP platform lived under `scrapers/infra/` while a thin
platform wrapper existed at `infra/main.bicep`. That split implied scraper
ownership of shared resources (ACR, Key Vault, n8n Container App, Postgres) and
duplicated mental model with the n8n canonicalization in ADR-0003.

## Decision

- **All platform Bicep** lives under repo root `infra/`.
- `infra/main.bicep` orchestrates `infra/scraper-stack.bicep` and optional StokAPI modules.
- `infra/modules/` holds shared Bicep modules (ACR, Postgres, Redis, Key Vault, Container Apps, n8n).
- **Deploy scripts** for full Azure stacks live in root `scripts/` (`deploy-scraper-azure.sh`, `deploy-scraper-azure-dev.sh`).
- Service folders (`scrapers/`, `muvstok-api/`) keep application code, tests, Dockerfiles, and service-specific ops scripts only — no `infra/` subfolder.
- CI workflows live only under `.github/workflows/` (no `scrapers/.github/workflows/`).

## Consequences

- `scrapers/infra/` removed; thin wrappers in `scrapers/scripts/deploy-azure*.sh` redirect to root scripts.
- `make bicep-validate` and `infra/README.md` are the canonical infra entry points.
- StokAPI Container Apps remain script-deployed until `infra/modules/stokapi-apps.bicep` is fully wired (Phase 6).
