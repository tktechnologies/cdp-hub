param name string
param containerName string
param location string
param environmentId string
param identityId string
param acrLoginServer string
param imageName string
@secure()
param databaseUrl string
@secure()
param databaseUrlSync string
@secure()
param redisUrl string
@secure()
param scrapeCacheRedisUrl string
@secure()
param celeryBrokerUrl string
@secure()
param celeryResultBackend string
@secure()
param apiKey string
@secure()
param callbackWebhookSecret string
@secure()
param meliboxUser string
@secure()
param meliboxPass string
@secure()
param proxyUrls string
param proxyRotationEnabled bool
param command array
param ingressExternal bool
param targetPort int
param minReplicas int
param maxReplicas int
param maxConcurrentScrapers int
param tags object

resource app 'Microsoft.App/containerApps@2024-03-01' = {
  name: name
  location: location
  tags: tags
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${identityId}': {}
    }
  }
  properties: {
    managedEnvironmentId: environmentId
    configuration: union({
      activeRevisionsMode: 'Single'
      registries: [
        {
          server: acrLoginServer
          identity: identityId
        }
      ]
      secrets: [
        {
          name: 'database-url'
          value: databaseUrl
        }
        {
          name: 'database-url-sync'
          value: databaseUrlSync
        }
        {
          name: 'redis-url'
          value: redisUrl
        }
        {
          name: 'scrape-cache-redis-url'
          value: scrapeCacheRedisUrl
        }
        {
          name: 'celery-broker-url'
          value: celeryBrokerUrl
        }
        {
          name: 'celery-result-backend'
          value: celeryResultBackend
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
          name: 'melibox-user'
          value: meliboxUser
        }
        {
          name: 'melibox-pass'
          value: meliboxPass
        }
        {
          name: 'proxy-urls'
          value: proxyUrls
        }
      ]
    }, ingressExternal ? {
      ingress: {
        external: true
        targetPort: targetPort
        transport: 'auto'
      }
    } : {})
    template: {
      containers: [
        {
          name: containerName
          image: imageName
          command: command
          env: [
            {
              name: 'DATABASE_URL'
              secretRef: 'database-url'
            }
            {
              name: 'DATABASE_URL_SYNC'
              secretRef: 'database-url-sync'
            }
            {
              name: 'REDIS_URL'
              secretRef: 'redis-url'
            }
            {
              name: 'SCRAPE_CACHE_REDIS_URL'
              secretRef: 'scrape-cache-redis-url'
            }
            {
              name: 'SCRAPE_CACHE_ENABLED'
              value: 'true'
            }
            {
              name: 'SCRAPE_CACHE_TTL_SECONDS'
              value: '86400'
            }
            {
              name: 'SCRAPE_CACHE_TTL_NOT_FOUND_SECONDS'
              value: '21600'
            }
            {
              name: 'SCRAPE_CACHE_TTL_BLOCKED_SECONDS'
              value: '1800'
            }
            {
              name: 'SCRAPE_CACHE_PG_FALLBACK'
              value: 'true'
            }
            {
              name: 'SCRAPE_SITES_SEQUENTIAL'
              value: 'false'
            }
            {
              name: 'CELERY_BROKER_URL'
              secretRef: 'celery-broker-url'
            }
            {
              name: 'CELERY_RESULT_BACKEND'
              secretRef: 'celery-result-backend'
            }
            {
              name: 'API_KEY'
              secretRef: 'api-key'
            }
            {
              name: 'CALLBACK_WEBHOOK_SECRET'
              secretRef: 'callback-webhook-secret'
            }
            {
              name: 'CREDENTIAL_MELIBOX_USER'
              secretRef: 'melibox-user'
            }
            {
              name: 'CREDENTIAL_MELIBOX_PASS'
              secretRef: 'melibox-pass'
            }
            {
              name: 'PROXY_URLS'
              secretRef: 'proxy-urls'
            }
            {
              name: 'PROXY_ROTATION_ENABLED'
              value: string(proxyRotationEnabled)
            }
            {
              name: 'PLAYWRIGHT_HEADLESS'
              value: 'true'
            }
            {
              name: 'MOCK_SCRAPERS'
              value: 'false'
            }
            {
              name: 'JOB_EXECUTION_BACKEND'
              value: 'celery'
            }
            {
              name: 'LOG_LEVEL'
              value: 'INFO'
            }
            {
              name: 'LOG_FORMAT'
              value: 'json'
            }
            {
              name: 'MAX_CONCURRENT_SCRAPERS'
              value: string(maxConcurrentScrapers)
            }
            {
              name: 'SCRAPE_DELAY_MIN'
              value: '2.0'
            }
            {
              name: 'SCRAPE_DELAY_MAX'
              value: '6.0'
            }
            {
              name: 'SCRAPER_ACTION_DELAY_MIN_MS'
              value: '400'
            }
            {
              name: 'SCRAPER_ACTION_DELAY_MAX_MS'
              value: '1400'
            }
            {
              name: 'MELIBOX_SKU_DELAY_MIN'
              value: '3'
            }
            {
              name: 'MELIBOX_SKU_DELAY_MAX'
              value: '8'
            }
            {
              name: 'CREDENTIAL_MELIBOX_URL'
              value: 'https://app.melibox.com.br/advProductPosition'
            }
            {
              name: 'CELERY_WORKER_PREFETCH_MULTIPLIER'
              value: '1'
            }
            {
              name: 'CELERY_TASK_TIME_LIMIT_SECONDS'
              value: '3600'
            }
          ]
          resources: {
            cpu: json('1.0')
            memory: '2Gi'
          }
        }
      ]
      scale: {
        minReplicas: minReplicas
        maxReplicas: maxReplicas
      }
    }
  }
}

output fqdn string = ingressExternal ? app.properties.configuration.ingress.fqdn : ''
output name string = app.name
