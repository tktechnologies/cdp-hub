param name string
param location string
param environmentId string
param imageName string
param databaseHost string
param databaseName string
param databaseUser string
@secure()
param databasePassword string
@secure()
param n8nEncryptionKey string
@secure()
param n8nBasicAuthUser string
@secure()
param n8nBasicAuthPassword string
param n8nHost string
param n8nEditorBaseUrl string
param n8nWebhookUrl string
@secure()
param apiKey string
@secure()
param callbackWebhookSecret string
param cdpScraperApiBase string
param cdpMuvstokApiBase string
param tags object

resource app 'Microsoft.App/containerApps@2024-03-01' = {
  name: name
  location: location
  tags: tags
  properties: {
    managedEnvironmentId: environmentId
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        targetPort: 5678
        transport: 'auto'
      }
      secrets: [
        {
          name: 'n8n-postgres-password'
          value: databasePassword
        }
        {
          name: 'n8n-encryption-key'
          value: n8nEncryptionKey
        }
        {
          name: 'n8n-basic-auth-user'
          value: n8nBasicAuthUser
        }
        {
          name: 'n8n-basic-auth-password'
          value: n8nBasicAuthPassword
        }
        {
          name: 'api-key'
          value: apiKey
        }
        {
          name: 'callback-webhook-secret'
          value: callbackWebhookSecret
        }
        {
          name: 'cdp-scrapers-api-base'
          value: cdpScraperApiBase
        }
        {
          name: 'cdp-muvstok-api-base'
          value: cdpMuvstokApiBase
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'n8n'
          image: imageName
          env: [
            {
              name: 'DB_TYPE'
              value: 'postgresdb'
            }
            {
              name: 'DB_POSTGRESDB_HOST'
              value: databaseHost
            }
            {
              name: 'DB_POSTGRESDB_PORT'
              value: '5432'
            }
            {
              name: 'DB_POSTGRESDB_DATABASE'
              value: databaseName
            }
            {
              name: 'DB_POSTGRESDB_USER'
              value: databaseUser
            }
            {
              name: 'DB_POSTGRESDB_PASSWORD'
              secretRef: 'n8n-postgres-password'
            }
            {
              name: 'DB_POSTGRESDB_SSL_ENABLED'
              value: 'true'
            }
            {
              name: 'N8N_ENCRYPTION_KEY'
              secretRef: 'n8n-encryption-key'
            }
            {
              name: 'N8N_BASIC_AUTH_ACTIVE'
              value: 'true'
            }
            {
              name: 'N8N_BASIC_AUTH_USER'
              secretRef: 'n8n-basic-auth-user'
            }
            {
              name: 'N8N_BASIC_AUTH_PASSWORD'
              secretRef: 'n8n-basic-auth-password'
            }
            {
              name: 'N8N_PORT'
              value: '5678'
            }
            {
              name: 'N8N_PROTOCOL'
              value: 'https'
            }
            {
              name: 'N8N_HOST'
              value: n8nHost
            }
            {
              name: 'N8N_EDITOR_BASE_URL'
              value: n8nEditorBaseUrl
            }
            {
              name: 'WEBHOOK_URL'
              value: n8nWebhookUrl
            }
            {
              name: 'CDP_SCRAPER_API_BASE'
              secretRef: 'cdp-scrapers-api-base'
            }
            {
              name: 'CDP_MUVSTOK_API_BASE'
              secretRef: 'cdp-muvstok-api-base'
            }
            {
              name: 'CDP_API_KEY'
              secretRef: 'api-key'
            }
            {
              name: 'CDP_MUVSTOK_API_KEY'
              secretRef: 'api-key'
            }
            {
              name: 'CDP_CALLBACK_WEBHOOK_SECRET'
              secretRef: 'callback-webhook-secret'
            }
            {
              name: 'CDP_MUVSTOK_CALLBACK_WEBHOOK_SECRET'
              secretRef: 'callback-webhook-secret'
            }
            {
              name: 'CALLBACK_WEBHOOK_SECRET'
              secretRef: 'callback-webhook-secret'
            }
            {
              name: 'CDP_N8N_WEBHOOK_PATH'
              value: 'webhook/scraper-result'
            }
            {
              name: 'CDP_MUVSTOK_WEBHOOK_PATH'
              value: 'webhook/muvstok-result'
            }
            {
              name: 'N8N_DIAGNOSTICS_ENABLED'
              value: 'false'
            }
            {
              name: 'N8N_VERSION_NOTIFICATIONS_ENABLED'
              value: 'false'
            }
          ]
          resources: {
            cpu: json('1.0')
            memory: '2Gi'
          }
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 1
      }
    }
  }
}

output fqdn string = app.properties.configuration.ingress.fqdn
output name string = app.name
