# AI Rules for This Project

**Tier 2b (StokAPI).** Platform/router rules: `../../.agent/rules.md` and `boundaries/platform.md`.

These rules define how AI agents must work in this repository. Follow them before making any code, spec, test, or documentation changes.

## Read Order

Before editing, read the project context in this order:

1. Read this file.
2. Read `index.md` and `boundaries/n8n.md` if touching n8n.
3. Read the relevant `.agent/memory/` files.
4. Read the relevant spec files.
5. Read related source code and tests.
6. Only then propose or make changes.

Do not mark work complete based on chat memory alone.

## Architecture Rules

- Keep API route handlers thin.
- Use this dependency direction for API work:

  API route -> service -> repository/client -> database, Redis, Azure, callback, or Muvstok

- Use this dependency direction for workers:

  worker -> service -> repository/client -> database, Redis, Azure, callback, or Muvstok

- PostgreSQL is the durable source of truth.
- Redis Streams are for coordination only.
- Never store the full SKU list in Redis.
- Process Muvstok SKUs sequentially within a job until the business explicitly approves more parallelism.
- Preserve resumability after every SKU or small batch.
- Use project-local patterns before introducing new abstractions.
- Do not mix extraction, transformation, orchestration, persistence, and external calls in one large file.
- Avoid huge files. Split code by responsibility when needed.

## Security Rules

- Never hardcode credentials.
- Never log, persist, print, or expose:
  - Raw tokens
  - API keys
  - Passwords
  - Connection strings
  - Authorization headers
  - Azure Key Vault values
  - Callback HMAC secrets
  - Personal data
  - Email addresses, unless explicitly required and safely handled
- Store Muvstok credentials in Azure Key Vault.
- Store only Key Vault references and token lifecycle metadata in PostgreSQL.
- Use environment variables or managed secret providers for configuration.
- Use Azure Managed Identity where possible.
- Validate callback URLs as public HTTPS.
- Keep improving SSRF protection around callback handling.
- Ask before changing production-like settings, credentials, deployments, or infrastructure configuration.

## Data Rules

- Never intentionally duplicate records.
- Always design writes to be idempotent where practical.
- Validate schema changes before relying on them.
- Treat `null` values explicitly.
- Document business rules that affect data behavior.
- Preserve existing data contracts unless the spec requires a change.
- When behavior changes, update the relevant spec.
- Worker `status=succeeded` means lookup completed — not a found-price signal.
  Canonical callback/Sheets semantics:
  [`../../.agent/rules/google-sheets.md`](../../.agent/rules/google-sheets.md).
- Detalhado seller output: `vendedor`, `uf`, `empresa`, `cnpj`; accept raw
  `estado` aliases but normalize to `uf` only.

## Testing and Validation Rules

- Local checks are useful feedback, but they are not the final done signal when production confidence is required.
- Official done/not-done decisions require Azure-hosted validation when the task depends on production-like behavior.
- Do not hide failed, skipped, blocked, flaky, or unwired tests.
- If a test cannot run, clearly state why.
- If Azure validation is unavailable, say exactly what was not validated.
- Prefer small, targeted tests that prove the changed behavior.
- Read existing tests before adding new test patterns.

## Observability Rules

- Add structured logs for:
  - Lifecycle transitions
  - Queue operations
  - Worker progress
  - Callback handling
  - Token checks
  - Error classifications
- Include `correlation_id` and `job_id` whenever available.
- Redact sensitive values before logging.
- Add metrics and traces when behavior crosses boundaries between:
  - API
  - Worker
  - Database
  - Redis
  - Muvstok
  - Azure
  - Callback systems

## Change Rules

- Keep edits scoped to the user’s task.
- Do not perform unrelated refactors.
- Update specs when behavior changes.
- Update `.agent/` when project memory, rules, patterns, risks, workflows, commands, or skills change.
- Prefer the smallest correct solution over a large risky one.
- If a change affects many files, pause and explain the impact before continuing.
- Do not introduce new dependencies unless clearly justified.
- Do not mark work complete until code, tests, docs, and validation status are all clear.

## Code Quality Rules

- Use clear, descriptive function and variable names.
- Add type hints where the project style supports them.
- Add useful error handling.
- Avoid swallowing exceptions silently.
- Keep functions focused on one responsibility.
- Keep files reasonably small.
- Avoid mixing extraction, transformation, orchestration, persistence, and external calls in the same function or file.
- Prefer explicit control flow over clever shortcuts.
- Match existing project style before introducing a new style.

## Sub-Agent Rules

- Use `sub-agents/` briefs only when the user explicitly asks for delegation, sub-agents, or parallel agent work.
- Give each sub-agent:
  - A clear ownership scope
  - Relevant files or specs to read
  - Expected output
  - Explicit boundaries
- Do not allow sub-agents to overlap writes unless the user explicitly accepts the coordination cost.
- The main agent remains responsible for integration, validation, and final reporting.

## Uncertainty Rules

- If requirements are unclear, ask before making risky changes.
- If the safe next step is obvious, proceed with the smallest reasonable implementation.
- If a task may affect production behavior, security, data integrity, or many files, explain the risk before proceeding.
- State assumptions clearly.
- State what was validated and what was not.
- Never pretend a task is complete when validation is missing or blocked.
