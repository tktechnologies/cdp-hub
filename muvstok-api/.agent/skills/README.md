# Skills

Project skills are reusable instructions for common Muvstok work.

Each skill folder should contain a `SKILL.md` with YAML frontmatter and concise workflow instructions. Avoid adding extra README files inside individual skill folders.

Current skills:

- `muvstok-implement-job-api`
- `muvstok-add-repository`
- `muvstok-add-migration`
- `muvstok-build-worker`
- `muvstok-redis-queue`
- `muvstok-azure-validation`

Each skill should define:

- when to use it
- source files and specs to read
- step-by-step workflow
- files it may update
- required validation
- docs or `.agent/` updates expected before completion

Good candidates include adding a FastAPI route, adding a repository, adding a migration, adding a worker task, publishing a Redis Stream message, adding structured logs, testing Key Vault integration, and testing Redis Stream workers.
