// CDP platform infrastructure entry (resource group scope).
// Orchestrates scraper stack (infra/scraper-stack.bicep) and optional StokAPI apps.

targetScope = 'resourceGroup'

@description('Deploy scraper stack (ACR, Postgres, Redis, Key Vault, Container Apps, n8n).')
param deployScraper bool = true

@description('Deploy StokAPI Container Apps module (placeholder — set true only after Phase 6 wiring).')
param deployStokapi bool = false

@description('Pass-through: scraper environment tag.')
param environmentName string = 'production'

@description('Pass-through: scraper pull identity name.')
param pullIdentityName string = 'cdp-scrapers-prod-pull'

@description('Scraper Postgres admin password.')
@secure()
param postgresAdminPassword string

@description('Scraper API key.')
@secure()
param apiKey string

@description('n8n / callback HMAC secret.')
@secure()
param callbackWebhookSecret string

@description('Proxy URLs JSON array for scrapers.')
@secure()
param proxyUrls string

@description('n8n encryption key.')
@secure()
param n8nEncryptionKey string

@description('n8n basic auth password.')
@secure()
param n8nBasicAuthPassword string

@secure()
param n8nBasicAuthUser string = 'admin'

@secure()
param meliboxUser string = ''
@secure()
param meliboxPass string = ''
@secure()
param muvstokUser string = ''
@secure()
param muvstokPassword string = ''
@secure()
param proxyAdminPassword string = ''

param deployContainerApps bool = true
param deployN8n bool = true
param deployProxyPool bool = false

module scraper 'scraper-stack.bicep' = if (deployScraper) {
  name: 'scraper-stack'
  params: {
    environmentName: environmentName
    pullIdentityName: pullIdentityName
    postgresAdminPassword: postgresAdminPassword
    apiKey: apiKey
    callbackWebhookSecret: callbackWebhookSecret
    proxyUrls: proxyUrls
    n8nEncryptionKey: n8nEncryptionKey
    n8nBasicAuthUser: n8nBasicAuthUser
    n8nBasicAuthPassword: n8nBasicAuthPassword
    meliboxUser: meliboxUser
    meliboxPass: meliboxPass
    muvstokUser: muvstokUser
    muvstokPassword: muvstokPassword
    proxyAdminPassword: proxyAdminPassword
    deployContainerApps: deployContainerApps
    deployN8n: deployN8n
    deployProxyPool: deployProxyPool
  }
}

module stokapiApps 'modules/stokapi-apps.bicep' = if (deployStokapi) {
  name: 'stokapi-apps'
  params: {
    environmentId: ''
    identityId: ''
    acrLoginServer: deployScraper ? scraper!.outputs.acrLoginServer : 'cdpscraperprodacr.azurecr.io'
    tags: {
      app: 'cdp-stokapi'
      environment: environmentName
    }
    deployContainerApps: false
  }
}

output scraperAcrLoginServer string = deployScraper ? scraper!.outputs.acrLoginServer : ''
output scraperApiFqdn string = deployScraper ? scraper!.outputs.apiContainerAppFqdn : ''
output scraperPostgresHost string = deployScraper ? scraper!.outputs.postgresHost : ''
output scraperRedisHost string = deployScraper ? scraper!.outputs.redisHost : ''
output scraperKeyVaultName string = deployScraper ? scraper!.outputs.keyVaultName : ''
output stokapiNote string = deployStokapi ? stokapiApps!.outputs.note : 'StokAPI module skipped (deployStokapi=false)'
