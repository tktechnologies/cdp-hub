# AGENTS.md — API Diversos

Instructions for AI agents working on this repository.

## Identity

Python 3.12 FastAPI ingestion platform for API Diversos SKU data. Accepts jobs with SKUs and a callback URL, queues via Redis Streams, processes SKU-by-SKU in workers, persists to PostgreSQL, delivers callbacks to n8n.

## Tier

| Tier | Entry |
|------|--------|
| **Platform** (router, dual pipeline, sync all workflows) | [../AGENTS.md](../AGENTS.md) → [../.agent/skills/n8n-router-sync/SKILL.md](../.agent/skills/n8n-router-sync/SKILL.md) |
| **This service** | This file → `.agent/index.md` |

## Read Order

1. `.agent/rules.md` — non-negotiable project rules
2. `.agent/index.md` — task router (what to read for each type of work)
3. `.agent/memory/implementation-state.md` — current deployment and feature state
4. Relevant `specs/` file for the area you're changing
5. Relevant `.agent/skills/` for reusable workflows

## Project Map

| Area | Path | Purpose |
|------|------|---------|
| Application code | `app/` | FastAPI API, workers, services, repos, clients, models |
| Specs | `specs/` | 12 planning specs (contracts, lifecycle, security, etc.) |
| Agent workspace | `.agent/` | Rules, memory, standards, skills, commands, sub-agents |
| n8n receiver JSON | `../../n8n/workflows/cdp_stokapi.json` | Canonical workflow (monorepo root) |
| n8n docs | `n8n/docs/` | StokAPI receiver guide (not workflow JSON) |
| Scripts | `scripts/` | Deploy, sync, audit, and ops scripts |
| Docker | `docker/` | Dockerfiles (API + worker) and local compose |
| Docs | `docs/` | Production audit results |
| Tests | `tests/` | Test directory (tests not yet implemented) |
| Infra | `infra/` | Azure infrastructure (placeholder) |

## Quality Gates

- `uv run ruff check .`
- `uv run mypy .`
- `uv run pytest` (when tests exist)
- `bash scripts/check_specs.sh`

## Key Constraints

- Production code lives under `app/`, not `src/`.
- PostgreSQL is the source of truth; Redis is coordination only.
- Secrets belong in Azure Key Vault, never in logs or plain DB fields.
- Official validation requires Azure-hosted environments.
- n8n: `cdp_stokapi` receiver in this repo; production dispatch is inline in monorepo `cdp_router` via `n8n/src/router_stokapi.js` (not Execute Workflow).
- Platform docs: `../docs/PLATFORM_OVERVIEW.md`, `../docs/architecture/DUAL_PIPELINE.md`.
