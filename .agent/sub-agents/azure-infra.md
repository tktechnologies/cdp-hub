# Azure Infra Agent (Platform)

## Ownership

Azure Container Apps, Key Vault references, ACR images, Log Analytics, and deploy scripts — not application business logic.

## Read First

- [docs/ARCHITECTURE.md](../../docs/ARCHITECTURE.md) (Azure section)
- `scrapers/infra/`, `scrapers/scripts/deploy-azure.sh`
- `muvstok-api/scripts/deploy_muv_api.sh`, `deploy_muv_worker.sh`
- [muvstok-api/.agent/standards/azure-playbook.md](../../muvstok-api/.agent/standards/azure-playbook.md)

## Expected Output

- Resource or env var changes with rollout order (API vs worker).
- Cost/reliability note for new Azure services.
- No secrets in output — Key Vault secret names only.

## Boundaries

Do not change Pydantic schemas, n8n Code nodes, or workflow JSON without assigned scope.
