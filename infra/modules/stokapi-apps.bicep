// StokAPI (API Diversos) Container Apps — placeholder for Phase 6 consolidation.
// Wire API + worker images, Key Vault secret refs, and Redis stream env vars here.
// Production deploy today: muvstok-api/scripts/deploy_muv_api.sh and deploy_muv_worker.sh

@description('Azure region for StokAPI Container Apps.')
param location string = 'eastus2'

@description('Container Apps environment resource ID (shared with scraper stack).')
param environmentId string = ''

@description('User-assigned identity for ACR pull.')
param identityId string = ''

@description('ACR login server (e.g. cdpscraperprodacr.azurecr.io).')
param acrLoginServer string

@description('API container image (placeholder).')
param apiImageName string = 'cdpscraperprodacr.azurecr.io/muvstok-api:latest'

@description('Worker container image (placeholder).')
param workerImageName string = 'cdpscraperprodacr.azurecr.io/muvstok-worker:latest'

param apiContainerAppName string = 'cdp-muv-api'
param workerContainerAppName string = 'cdp-muv-worker-prod'
param tags object

@description('When false, skip creating resources (scaffold only).')
param deployContainerApps bool = false

// Placeholder outputs — replace with real module resources when consolidating deploy.
output apiContainerAppName string = deployContainerApps ? apiContainerAppName : ''
output workerContainerAppName string = deployContainerApps ? workerContainerAppName : ''
output apiFqdn string = ''
output note string = 'StokAPI Bicep not yet wired — use muvstok-api deploy scripts'
