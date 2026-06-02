# Agent Rule Index

Task-scoped agent rules live here so the CDP repo has one project-owned
agent documentation workspace: `.agent/`.

Use these as short context files when a task is limited to one surface. The
canonical details remain in `AGENTS.md`, service `AGENTS.md` files, and the
linked `.agent/` standards, boundaries, skills, and memory files.

For cross-service ownership, start with [../knowledge/service-catalog.md](../knowledge/service-catalog.md).

| Rule | Applies to |
|------|------------|
| [platform.md](platform.md) | Whole-monorepo and cross-service work |
| [n8n.md](n8n.md) | `n8n/**`, router Code, workflow JSON |
| [scraper.md](scraper.md) | `scrapers/**` |
| [stokapi.md](stokapi.md) | `muvstok-api/**` |
| [python.md](python.md) | Python service code |
| [contracts.md](contracts.md) | `contracts/**` JSON Schemas |
| [infrastructure.md](infrastructure.md) | `infra/**`, Azure deploy and Bicep |
