// ---------------------------------------------------------------------------
// Module: Function App (UI API) + App Service Plan + Managed Identity
// ---------------------------------------------------------------------------

param location string
param functionAppName string
param appServicePlanName string
param storageAccountName string
param appInsightsConnectionString string
param appInsightsInstrumentationKey string
param tenantId string
param apiClientId string
param pythonVersion string
param tags object

// VNet integration params (only used when enableVnetIntegration = true)
param enableVnetIntegration bool = false
param vnetIntegrationSubnetId string = ''

// ── App Service Plan (Flex Consumption for VNet, Consumption otherwise) ─────

resource appServicePlan 'Microsoft.Web/serverfarms@2024-04-01' = {
  name: appServicePlanName
  location: location
  tags: tags
  kind: 'linux'
  sku: enableVnetIntegration
    ? {
        tier: 'FlexConsumption'
        name: 'FC1'
      }
    : {
        tier: 'Dynamic'
        name: 'Y1'
      }
  properties: {
    reserved: true // Required for Linux
  }
}

// ── Function App ────────────────────────────────────────────────────────────

resource functionApp 'Microsoft.Web/sites@2024-04-01' = {
  name: functionAppName
  location: location
  tags: union(tags, { 'azd-service-name': 'api' })
  kind: 'functionapp,linux'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: appServicePlan.id
    httpsOnly: true
    virtualNetworkSubnetId: enableVnetIntegration ? vnetIntegrationSubnetId : null
    siteConfig: {
      linuxFxVersion: 'Python|${pythonVersion}'
      pythonVersion: pythonVersion
      ftpsState: 'Disabled'
      minTlsVersion: '1.2'
      http20Enabled: true
      cors: {
        allowedOrigins: [
          'https://*.azurestaticapps.net'
        ]
        supportCredentials: true
      }
      appSettings: [
        {
          name: 'FUNCTIONS_WORKER_RUNTIME'
          value: 'python'
        }
        {
          name: 'FUNCTIONS_EXTENSION_VERSION'
          value: '~4'
        }
        {
          name: 'AzureWebJobsStorage__accountName'
          value: storageAccountName
        }
        {
          name: 'AZURE_STORAGE_ACCOUNT_URL'
          value: 'https://${storageAccountName}.blob.${environment().suffixes.storage}'
        }
        {
          name: 'AZURE_TENANT_ID'
          value: tenantId
        }
        {
          name: 'AZURE_CLIENT_ID'
          value: apiClientId
        }
        {
          name: 'BRONZE_CONTAINER'
          value: 'bronze'
        }
        {
          name: 'GOLD_CONTAINER'
          value: 'gold'
        }
        {
          name: 'METADATA_CONTAINER'
          value: 'ui-metadata'
        }
        {
          name: 'MAX_UPLOAD_SIZE_MB'
          value: '20'
        }
        {
          name: 'ALLOWED_EXTENSIONS'
          value: 'jpg,jpeg,png'
        }
        {
          name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
          value: appInsightsConnectionString
        }
        {
          name: 'APPINSIGHTS_INSTRUMENTATIONKEY'
          value: appInsightsInstrumentationKey
        }
      ]
    }
  }
}

// ── Outputs ─────────────────────────────────────────────────────────────────

output functionAppName string = functionApp.name
output functionAppHostname string = functionApp.properties.defaultHostName
output functionAppPrincipalId string = functionApp.identity.principalId
output functionAppResourceId string = functionApp.id
