# Infrastructure Rules

**Applies to:** `infra/**`, service infra folders, Azure deploy scripts, and Key Vault work.

- Platform Bicep: `infra/main.bicep`; validate with `make bicep-validate`.
- Service stacks: `scrapers/infra/` and `muvstok-api/infra/` when present.
- Secrets flow from Azure Key Vault to Container App env; never commit real values in parameters, Bicep outputs, docs, or agent memory.
- Default resource group for what-if checks: `automation` (override with `AZURE_RESOURCE_GROUP`).
- Do not deploy or mutate live Azure resources without explicit user approval.
