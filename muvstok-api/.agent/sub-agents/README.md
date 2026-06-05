# API Diversos Sub-Agents

Use these only when the user explicitly asks for delegation, sub-agents, or
parallel agent work. Keep writes scoped so delegated agents do not overlap.

| Agent | File | Scope |
|-------|------|-------|
| API service | [api-service-agent.md](api-service-agent.md) | Routes, schemas, job submission and inspection |
| Worker queue | [worker-queue-agent.md](worker-queue-agent.md) | Redis Streams worker, job processing lifecycle |
| Database | [database-agent.md](database-agent.md) | PostgreSQL models, migrations, repositories |
| Security review | [security-review-agent.md](security-review-agent.md) | Secrets, auth, callback validation, Key Vault |
| Azure validation | [azure-validation-agent.md](azure-validation-agent.md) | Container Apps deploy, hosted smoke and audit |
| Docs memory | [docs-memory-agent.md](docs-memory-agent.md) | Specs, implementation-state, agent workspace docs |
