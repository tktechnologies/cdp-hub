param name string
param location string
param deployN8n bool = true
@secure()
param apiKey string
@secure()
param callbackWebhookSecret string
@secure()
param databaseUrl string
@secure()
param databaseUrlSync string
@secure()
param redisUrl string
@secure()
param celeryBrokerUrl string
@secure()
param celeryResultBackend string
@secure()
param meliboxUser string
@secure()
param meliboxPass string
@secure()
param muvstokUser string = ''
@secure()
param muvstokPassword string = ''
@secure()
param proxyUrls string
@secure()
param n8nDatabaseUrl string
@secure()
param n8nEncryptionKey string
@secure()
param n8nBasicAuthUser string
@secure()
param n8nBasicAuthPassword string
param cdpScraperApiBase string
param cdpMuvstokApiBase string
param tags object

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: name
  location: location
  tags: tags
  properties: {
    tenantId: subscription().tenantId
    sku: {
      family: 'A'
      name: 'standard'
    }
    enableRbacAuthorization: true
    enabledForTemplateDeployment: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 7
  }
}

resource apiKeySecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  name: 'api-key'
  parent: keyVault
  properties: {
    value: apiKey
  }
}

resource callbackSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  name: 'callback-webhook-secret'
  parent: keyVault
  properties: {
    value: callbackWebhookSecret
  }
}

resource databaseUrlSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  name: 'database-url'
  parent: keyVault
  properties: {
    value: databaseUrl
  }
}

resource databaseUrlSyncSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  name: 'database-url-sync'
  parent: keyVault
  properties: {
    value: databaseUrlSync
  }
}

resource redisUrlSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  name: 'redis-url'
  parent: keyVault
  properties: {
    value: redisUrl
  }
}

resource celeryBrokerUrlSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  name: 'celery-broker-url'
  parent: keyVault
  properties: {
    value: celeryBrokerUrl
  }
}

resource celeryResultBackendSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  name: 'celery-result-backend'
  parent: keyVault
  properties: {
    value: celeryResultBackend
  }
}

resource meliboxUserSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  name: 'melibox-user'
  parent: keyVault
  properties: {
    value: meliboxUser
  }
}

resource meliboxPassSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  name: 'melibox-pass'
  parent: keyVault
  properties: {
    value: meliboxPass
  }
}

resource proxyUrlsSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  name: 'proxy-urls'
  parent: keyVault
  properties: {
    value: proxyUrls
  }
}

resource muvstokUserSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  name: 'muvstok-user'
  parent: keyVault
  properties: {
    value: muvstokUser
  }
}

resource muvstokPasswordSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  name: 'muvstok-password'
  parent: keyVault
  properties: {
    value: muvstokPassword
  }
}

resource n8nDatabaseUrlSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = if (deployN8n) {
  name: 'n8n-database-url'
  parent: keyVault
  properties: {
    value: n8nDatabaseUrl
  }
}

resource n8nEncryptionKeySecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = if (deployN8n) {
  name: 'n8n-encryption-key'
  parent: keyVault
  properties: {
    value: n8nEncryptionKey
  }
}

resource n8nBasicAuthUserSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = if (deployN8n) {
  name: 'n8n-basic-auth-user'
  parent: keyVault
  properties: {
    value: n8nBasicAuthUser
  }
}

resource n8nBasicAuthPasswordSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = if (deployN8n) {
  name: 'n8n-basic-auth-password'
  parent: keyVault
  properties: {
    value: n8nBasicAuthPassword
  }
}

resource cdpScraperApiBaseSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  name: 'cdp-scrapers-api-base'
  parent: keyVault
  properties: {
    value: cdpScraperApiBase
  }
}

resource cdpMuvstokApiBaseSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  name: 'cdp-muvstok-api-base'
  parent: keyVault
  properties: {
    value: cdpMuvstokApiBase
  }
}

output id string = keyVault.id
output name string = keyVault.name
