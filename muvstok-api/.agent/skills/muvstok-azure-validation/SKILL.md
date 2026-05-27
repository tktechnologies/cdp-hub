---
name: muvstok-azure-validation
description: Plan, wire, run, or interpret Azure-hosted validation for Muvstok API. Use when changing scripts/azure_test.sh, CI/CD, Azure Container Apps validation, Azure PostgreSQL or Redis integration tests, Key Vault validation, cloud logs, or official done/not-done evidence.
---

# Muvstok Azure Validation

## Overview

Use this skill to keep production confidence tied to Azure-hosted evidence instead of local-only checks.

## Read First

- `.agent/rules.md`
- `.agent/standards/testing-playbook.md`
- `.agent/standards/azure-playbook.md`
- `specs/005-testing-strategy.md`
- `specs/009-azure-infrastructure.md`
- `specs/012-operational-runbook.md`
- `scripts/azure_test.sh`
- `Makefile`

## Workflow

1. Identify which Azure resources are needed: API, worker, PostgreSQL, Redis, Key Vault-compatible secrets, logs.
2. Define the evidence needed for the task: test report, API response, DB assertion, Redis assertion, logs, traces, or metrics.
3. Wire `scripts/azure_test.sh` or CI/CD to run the required checks.
4. Capture correlation IDs for API and worker flows.
5. Report exact commands, environment, and pass/fail evidence.
6. If blocked, say what is not wired and what cannot be claimed.
7. Update `.agent/commands/azure-validation.md` when the stable command changes.

## Validation Layers

- Unit tests in Azure CI workers.
- Integration tests against Azure-hosted PostgreSQL and Redis.
- Contract tests against Azure-deployed FastAPI OpenAPI behavior.
- End-to-end tests from job submission through callback behavior.

## Watch Points

- `scripts/azure_test.sh` is currently a placeholder.
- Do not add Azure services without explicit cost, reliability, and operational trade-off notes.
