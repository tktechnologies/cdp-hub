# Agent Index

Use this file to decide what to read before acting.

## Tier

**Tier 2b (StokAPI).** Router / dual pipeline / platform workflow sync → [../../.agent/index.md](../../.agent/index.md) (platform).

Root service catalog: [../../.agent/knowledge/service-catalog.md](../../.agent/knowledge/service-catalog.md).

## Always Read First

1. `rules.md`
2. `memory/project-memory.md`
3. `memory/implementation-state.md` (StokAPI runtime — not live n8n IDs)
4. Relevant spec in `specs/`
5. Relevant skill in `skills/`

If the task is **only** router or cross-service: stop and use platform tier first.

## Task Routing

- API route, schema, auth, or endpoint behavior: read `skills/muvstok-implement-job-api/SKILL.md`, `specs/002-api-contract.md`, `app/api/`, `app/schemas/`, and `app/services/job_service.py`.
- Database model, repository, query, or migration: read `skills/muvstok-add-repository/SKILL.md`, `skills/muvstok-add-migration/SKILL.md`, `specs/004-database-design.md`, `app/db/models.py`, `app/repositories/`, and migrations.
- Redis Streams, worker queueing, ack, retry, pending, or dead-letter behavior: read `skills/muvstok-redis-queue/SKILL.md`, `specs/010-queue-processing.md`, `app/clients/redis_queue_client.py`, `app/services/queue_service.py`, and `app/workers/redis_worker.py`.
- Worker job/SKU processing: read `skills/muvstok-build-worker/SKILL.md`, `specs/003-job-lifecycle.md`, `app/workers/`, `app/services/`, `app/repositories/`, and `app/clients/muvstok_client.py`.
- Result/status classification for callbacks or Sheets: read
  `specs/002-api-contract.md`, `specs/003-job-lifecycle.md`,
  `app/domain/sku_result_status.py`, `app/services/callback_service.py`, and
  `n8n/lib/muvstok_sheet_helpers.js`.
  Detalhado seller fields are `uf`, `empresa`, `cnpj`; `estado` is an input
  alias only.
- Azure validation, deployment, or cloud test work: read `skills/muvstok-azure-validation/SKILL.md`, `standards/azure-playbook.md`, `standards/testing-playbook.md`, and `scripts/azure_test.sh`.
- Security, secrets, callback URLs, API keys, or log redaction: read `standards/security-and-secrets.md`, `specs/008-security-and-secrets.md`, and `app/core/security.py`.
- Observability, logs, metrics, or traces: read `standards/observability.md`, `specs/007-observability.md`, `app/core/logging.py`, and `app/observability/`.
- n8n receiver (`cdp_stokapi` only): `n8n/workflows/cdp_stokapi.json`, `n8n/settings/cdp_stokapi.json`, `muvstok-api/n8n/docs/MUVSTOK_N8N_WORKFLOW_GUIDE.md`, `boundaries/n8n.md`
- n8n router / dispatch / platform workflow sync: **platform** `../../.agent/skills/n8n-router-sync/SKILL.md` + `n8n/src/router_stokapi.js`
- Code review: read `workflows/review-checklist.md` and the relevant standards.

## Completion Routing

Before marking work done:

- Update affected specs if behavior changed.
- Update affected `.agent/` memory, standards, workflows, skills, commands, or sub-agent briefs.
- Run the relevant local checks as feedback.
- Record whether Azure validation was run, skipped, or still blocked.
