targetScope = 'resourceGroup'

@description('Azure region for PostgreSQL Flexible Server.')
param postgresLocation string = 'brazilsouth'

@description('Azure region for ACR, Redis, Key Vault, Log Analytics, Container Apps, API, worker, and N8N.')
param appLocation string = 'eastus2'

@description('Environment name used in resource tags.')
param environmentName string = 'production'

param acrName string = 'cdpscraperprodacr'
param containerAppEnvironmentName string = 'cdp-scrapers-prod-env'
param apiContainerAppName string = 'cdp-scrapers-api-prod'
param workerContainerAppName string = 'cdp-scrapers-worker-prod'
param n8nContainerAppName string = 'cdp-n8n-prod'
param imageName string = 'cdpscraperprodacr.azurecr.io/cdp-scraper:latest'
param n8nImageName string = 'docker.io/n8nio/n8n:latest'
param n8nHost string = 'automacao.tktechnologies.com.br'
param n8nEditorBaseUrl string = 'https://automacao.tktechnologies.com.br'
param n8nWebhookUrl string = 'https://automacao.tktechnologies.com.br/'
param cdpScraperApiBase string = 'https://cdp-scrapers-api-prod.bravecoast-b14d791e.eastus2.azurecontainerapps.io'
param cdpMuvstokApiBase string = 'https://cdp-muv-api.bravecoast-b14d791e.eastus2.azurecontainerapps.io'
param postgresServerName string = 'cdp-scrapers-pg-prod'
param postgresDatabaseName string = 'cdp_scraper'
param n8nDatabaseName string = 'n8n'
param postgresAdminUser string = 'cdp'
@secure()
param postgresAdminPassword string
param redisName string = 'cdp-scrapers-redis-prod'
param keyVaultName string = 'cdp-scrapers-kv-prod'
@secure()
param apiKey string
@secure()
param callbackWebhookSecret string
@secure()
param meliboxUser string = ''
@secure()
param meliboxPass string = ''
@secure()
param proxyUrls string
param proxyRotationEnabled bool = true
param maxConcurrentScrapers int = 3
param workerMaxConcurrentScrapers int = 2
param deployContainerApps bool = true
param deployProxyPool bool = false
param proxyAdminUsername string = 'proxyadmin'
@secure()
param proxyAdminPassword string = ''
@secure()
param n8nEncryptionKey string
param n8nBasicAuthUser string = 'admin'
@secure()
param n8nBasicAuthPassword string

var tags = {
  app: 'cdp-scraper'
  environment: environmentName
}

var meliboxUserSecretValue = empty(meliboxUser) ? 'not-configured' : meliboxUser
var meliboxPassSecretValue = empty(meliboxPass) ? 'not-configured' : meliboxPass
var databaseUrl = 'postgresql+asyncpg://${postgresAdminUser}:${postgresAdminPassword}@${postgres.outputs.hostName}/${postgresDatabaseName}?ssl=require'
var databaseUrlSync = 'postgresql://${postgresAdminUser}:${postgresAdminPassword}@${postgres.outputs.hostName}/${postgresDatabaseName}?sslmode=require'
var redisUrl = 'rediss://:${redis.outputs.primaryKey}@${redis.outputs.hostName}:6380/0'
var scrapeCacheRedisUrl = 'rediss://:${redis.outputs.primaryKey}@${redis.outputs.hostName}:6380/1'
var celeryRedisUrl = '${redisUrl}?ssl_cert_reqs=CERT_NONE'
var n8nDatabaseUrl = 'postgresql://${postgresAdminUser}:${postgresAdminPassword}@${postgres.outputs.hostName}/${n8nDatabaseName}?sslmode=require'

module acr 'modules/acr.bicep' = {
  name: 'acr'
  params: {
    name: acrName
    location: appLocation
    tags: tags
  }
}

module identity 'modules/identity.bicep' = {
  name: 'container-app-pull-identity'
  params: {
    name: 'cdp-scrapers-prod-pull'
    location: appLocation
    tags: tags
  }
}

resource acrPullRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(resourceGroup().id, acrName, 'cdp-scrapers-prod-pull', 'AcrPull')
  scope: resourceGroup()
  properties: {
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      '7f951dda-4ed3-4680-a7ca-43fe172d538d'
    )
    principalId: identity.outputs.principalId
    principalType: 'ServicePrincipal'
  }
}

module postgres 'modules/postgres.bicep' = {
  name: 'postgres'
  params: {
    serverName: postgresServerName
    databaseName: postgresDatabaseName
    n8nDatabaseName: n8nDatabaseName
    adminUser: postgresAdminUser
    adminPassword: postgresAdminPassword
    location: postgresLocation
    tags: tags
  }
}

module redis 'modules/redis.bicep' = {
  name: 'redis'
  params: {
    name: redisName
    location: appLocation
    tags: tags
  }
}

module keyVault 'modules/key-vault.bicep' = {
  name: 'key-vault'
  params: {
    name: keyVaultName
    location: appLocation
    apiKey: apiKey
    callbackWebhookSecret: callbackWebhookSecret
    databaseUrl: databaseUrl
    databaseUrlSync: databaseUrlSync
    redisUrl: redisUrl
    celeryBrokerUrl: celeryRedisUrl
    celeryResultBackend: celeryRedisUrl
    meliboxUser: meliboxUserSecretValue
    meliboxPass: meliboxPassSecretValue
    proxyUrls: proxyUrls
    n8nDatabaseUrl: n8nDatabaseUrl
    n8nEncryptionKey: n8nEncryptionKey
    n8nBasicAuthUser: n8nBasicAuthUser
    n8nBasicAuthPassword: n8nBasicAuthPassword
    cdpScraperApiBase: cdpScraperApiBase
    cdpMuvstokApiBase: cdpMuvstokApiBase
    tags: tags
  }
}

module appEnv 'modules/container-app-env.bicep' = {
  name: 'container-app-env'
  params: {
    name: containerAppEnvironmentName
    location: appLocation
    tags: tags
  }
}

module apiContainerApp 'modules/container-app.bicep' = if (deployContainerApps) {
  name: 'scrapers-api-container-app'
  params: {
    name: apiContainerAppName
    containerName: 'scraper-api'
    location: appLocation
    environmentId: appEnv.outputs.id
    identityId: identity.outputs.id
    acrLoginServer: acr.outputs.loginServer
    imageName: imageName
    command: []
    ingressExternal: true
    targetPort: 8000
    minReplicas: 1
    maxReplicas: 3
    maxConcurrentScrapers: maxConcurrentScrapers
    databaseUrl: databaseUrl
    databaseUrlSync: databaseUrlSync
    redisUrl: redisUrl
    scrapeCacheRedisUrl: scrapeCacheRedisUrl
    celeryBrokerUrl: celeryRedisUrl
    celeryResultBackend: celeryRedisUrl
    apiKey: apiKey
    callbackWebhookSecret: callbackWebhookSecret
    meliboxUser: meliboxUserSecretValue
    meliboxPass: meliboxPassSecretValue
    proxyUrls: proxyUrls
    proxyRotationEnabled: proxyRotationEnabled
    tags: tags
  }
  dependsOn: [
    acrPullRole
    keyVault
  ]
}

module workerContainerApp 'modules/container-app.bicep' = if (deployContainerApps) {
  name: 'scrapers-worker-container-app'
  params: {
    name: workerContainerAppName
    containerName: 'scraper-worker'
    location: appLocation
    environmentId: appEnv.outputs.id
    identityId: identity.outputs.id
    acrLoginServer: acr.outputs.loginServer
    imageName: imageName
    command: [
      'celery'
      '-A'
      'src.celery_app.celery_app'
      'worker'
      '--loglevel=INFO'
      '--concurrency=1'
    ]
    ingressExternal: false
    targetPort: 8000
    minReplicas: 1
    maxReplicas: 1
    maxConcurrentScrapers: workerMaxConcurrentScrapers
    databaseUrl: databaseUrl
    databaseUrlSync: databaseUrlSync
    redisUrl: redisUrl
    scrapeCacheRedisUrl: scrapeCacheRedisUrl
    celeryBrokerUrl: celeryRedisUrl
    celeryResultBackend: celeryRedisUrl
    apiKey: apiKey
    callbackWebhookSecret: callbackWebhookSecret
    meliboxUser: meliboxUserSecretValue
    meliboxPass: meliboxPassSecretValue
    proxyUrls: proxyUrls
    proxyRotationEnabled: proxyRotationEnabled
    tags: tags
  }
  dependsOn: [
    acrPullRole
    keyVault
  ]
}

module n8nContainerApp 'modules/n8n-container-app.bicep' = if (deployContainerApps) {
  name: 'n8n-container-app'
  params: {
    name: n8nContainerAppName
    location: appLocation
    environmentId: appEnv.outputs.id
    imageName: n8nImageName
    databaseHost: postgres.outputs.hostName
    databaseName: n8nDatabaseName
    databaseUser: postgresAdminUser
    databasePassword: postgresAdminPassword
    n8nEncryptionKey: n8nEncryptionKey
    n8nBasicAuthUser: n8nBasicAuthUser
    n8nBasicAuthPassword: n8nBasicAuthPassword
    n8nHost: n8nHost
    n8nEditorBaseUrl: n8nEditorBaseUrl
    n8nWebhookUrl: n8nWebhookUrl
    apiKey: apiKey
    callbackWebhookSecret: callbackWebhookSecret
    cdpScraperApiBase: cdpScraperApiBase
    cdpMuvstokApiBase: cdpMuvstokApiBase
    tags: tags
  }
  dependsOn: [
    keyVault
  ]
}

module proxyPool 'modules/proxy-pool.bicep' = if (deployProxyPool) {
  name: 'proxy-pool'
  params: {
    location: appLocation
    adminUsername: proxyAdminUsername
    adminPassword: proxyAdminPassword
    tags: tags
  }
}

output acrLoginServer string = acr.outputs.loginServer
output apiContainerAppFqdn string = deployContainerApps ? apiContainerApp!.outputs.fqdn : ''
output workerContainerAppName string = deployContainerApps ? workerContainerApp!.outputs.name : ''
output n8nContainerAppFqdn string = deployContainerApps ? n8nContainerApp!.outputs.fqdn : ''
output postgresHost string = postgres.outputs.hostName
output redisHost string = redis.outputs.hostName
output keyVaultName string = keyVault.outputs.name
output proxyPublicIps array = deployProxyPool ? proxyPool!.outputs.publicIpAddresses : []
